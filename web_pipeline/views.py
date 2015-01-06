import os
from tempfile import mkdtemp
from shutil import copyfile
from random import randint

from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.conf import settings
from django.utils.timezone import now

from web_pipeline.models import Job, JobToMut, Mut, Protein, Mutation, Imutation, HGNCIdentifier, UniprotIdentifier, Domain
from web_pipeline.functions import getPnM, getResultData, isInvalidMut, fetchProtein, sendEmail, checkForCompletion
from web_pipeline.tasks import sleepabit, runPipelineWrapper

try:
    os.environ['MPLCONFIGDIR'] = mkdtemp()
    from pipeline.code.elaspic import blacklisted_uniprots
except ImportError:
    blacklisted_uniprots = []



def inp(request, p):
    context = {
        'current': p,
        'type': 'input',
        'test': request.META['HTTP_HOST']
    }
    return render(request, p + '.html', context)
    

def runPipeline(request):
    
    # Check for valid request.
    if not request.GET:
        raise Http404
    if not 'proteins' in request.GET or not 'email' in request.GET:
        raise Http404
    if not request.GET['proteins'].strip():
        return HttpResponseRedirect('/') # No protein input.

    # Generate list of valid proteins and mutations.
    pnms = request.GET['proteins'].split(' ')[:100]
    validPnms = []
    for pnm in pnms:
        iden, mut = getPnM(pnm)
        p = fetchProtein(iden)
        if not p:
            continue
        if isInvalidMut(mut, p.seq):
            continue
        validPnms.append([p.id, mut, iden])
    if not validPnms:
        return HttpResponseRedirect('/') # No valid proteins.

    # Create job in database.
    while True:
        randomID = "%06x" % randint(1,16777215)
        if Job.objects.filter(jobID=randomID).count() == 0:
            break
    j = Job.objects.create(jobID = randomID, 
                           email = request.GET['email'],
                           browser = request.META['HTTP_USER_AGENT'])

    # Create mutations in database if not already there.
    newMuts, doneMuts = [], []
    for pnm in validPnms:
        toRerun = False
        m = Mut.objects.filter(protein=pnm[0], mut=pnm[1])
        # Check for blacklisted uniprots and skip.
        if pnm[0] in blacklisted_uniprots:
            if m:
                mut = m[0]
                mut.status = 'error'
                mut.affectedType = ''
                mut.error = '5: Blacklisted'
                mut.save()
                doneMuts.append([mut, pnm[2]])
            else:
                doneMuts.append([Mut.objects.create(protein=pnm[0], mut=pnm[1], 
                                                    status='error', 
                                                    error='5: Blaclisted'), pnm[2]])
            checkForCompletion(doneMuts[-1][0].jobs.all())
            continue

        # Get potential results.
        muts = list(Mutation.objects.using('data').filter(protein_id=pnm[0], mut=pnm[1]))
        imuts = list(Imutation.objects.using('data').filter(protein_id=pnm[0], mut=pnm[1]))

        if m:
            mut = m[0]
            typ = mut.affectedType
            
            # Add rerun mutations to run list. Reasons:
            # 1) Mutation data disappeared from ELASPIC database.
            # 2) Mutation data changed from core to interface.
            # 3) Mutation data changed from not in domain.
            # 4) Pipeline crashed or ran out of time on last run.
            if (typ == 'CO' and not muts) or (typ == 'IN' and not imuts)\
              or (typ == 'CO' and imuts)\
              or (typ == 'NO' and (muts or imuts))\
              or (mut.error and (mut.error[0] != '1')):
                toRerun = True

            # Add mutations to lists.
            if toRerun and not(mut.rerun):
                mut.rerun = True
                mut.save()
                newMuts.append([mut, pnm[2]])
            else:
                doneMuts.append([mut, pnm[2]])
        else:
            # Create new mutations if the result isn't already complete.
            if (not(imuts) and muts and all([mut.ddG for mut in muts]))\
              or (imuts and all([mut.ddG for mut in imuts])):
                doneMuts.append([Mut.objects.create(protein=pnm[0], 
                                                    mut=pnm[1],
                                                    status='done',
                                                    affectedType='IN' if imuts else 'CO',
                                                    dateFinished=now()), pnm[2]])
            else:
                newMuts.append([Mut.objects.create(protein=pnm[0], mut=pnm[1]), pnm[2]])

    # Link all mutations to job.
    JobToMut.objects.bulk_create([JobToMut(job=j, mut=allMuts[0], inputIdentifier=allMuts[1]) for allMuts in doneMuts + newMuts])   

    # ##### Run pipeline #####
    #

    # Run pipeline for new mutations.
    for m in newMuts:
        mut = m[0]
        p = runPipelineWrapper.delay(mut, randomID)
        mut.taskId = p.task_id
        mut.save()
    
    #
    # ##### ############ #####

    # Set job to done if all mutations are already done.
    if all([(True if (m[0].status == 'done' or m[0].status == 'error') and \
            not(m[0].rerun) else False) for m in newMuts + doneMuts]):
        j.isDone = True
        j.dateFinished = now()
        j.save()
        # Send completion email.
        sendEmail(j, 'complete')
    if not j.isDone:
        # Send start email.
        sendEmail(j, 'started')

    # Redirect to result page.   
    return HttpResponseRedirect('http://%s/result/%s/' % (request.get_host(), randomID))


def displayResult(request):

    # Check if request ID is legit.
    requestID = request.path.split('/')[2]
    try:
        job = Job.objects.get(jobID=requestID)
    except Job.DoesNotExist:
        raise Http404
        
#    # Check for crashed tasks.
#    if not(job.isDone):
#        c = CleanupManager(dosleep=False)
#        c.checkForStalledMuts(requestID)

    # Fetch data
    data = [getResultData(jtom) for jtom in job.jobtomut_set.all()]
    for m in data:
        
        # Set mutation status temporarily as 'running' if its rerunning.
        if m.mut.rerun and not(job.isDone):
            if m.mut.rerun == 2:
                m.mut.status = 'running'
            else:
                m.mut.status = 'queued'
        # Get additional data for result table.
        doneInt, toRemove = [], []
        if not m.realMutErr:
            for i, mut in enumerate(m.realMut):
                chain = mut.findChain()
                # Get alignment scores.
                mut.alignscore = mut.model.template.getalignscore(chain)
                mut.seqid = mut.model.template.getsequenceidentity(chain)
                # Get interacting protein.
                if m.mut.affectedType == 'IN':
                    d = mut.model.template.domain.getdomain(1 if chain == 2 else 2)
                    if d.protein.id == m.mut.protein:
                        mut.inac = 'self'
                    else:
                        try:
                            mut.inac = HGNCIdentifier.objects.using('uniprot').get(identifierType='HGNC_genename', uniprotID=d.protein.id)
                        except HGNCIdentifier.DoesNotExist:
                            mut.inac = d.protein.name.split('_')[0]
                        except HGNCIdentifier.MultipleObjectsReturned:
                            mut.inac = HGNCIdentifier.objects.using('uniprot').filter(identifierType='HGNC_genename', uniprotID=d.protein.id)[0]
                    mut.inacd = 'h%d' % d.id if mut.inac == 'self' else 'n%d' % d.id
                    # Check for dublicates. Remove the last one. 
                    # This is a quick and dirty fix and should be fixed to pick 
                    # the highest sequence identity.
                    dubkey = '%s.%s.%d' % (m.mut.protein, m.mut.mut, d.id)
                    if dubkey in doneInt:
                        toRemove.append(i)
                    else:
                        doneInt.append(dubkey)
            for rem in toRemove:
                m.realMut.remove(m.realMut[rem])

    context = {
        'url': 'http://%s/result/%s/' % (request.get_host(), requestID),
        'type': 'result',
        'current': 'result',
        'isRunning': not(job.isDone),
        'job': job, #{'jobID': 'asd'},
        'data': data,
    }
    return render(request, 'result.html', context)


def displaySecondaryResult(request):
    
    # Check URL for session change.
    if request.GET:
        if 'j' in request.GET:
            request.session['jmol'] = request.GET['j']
            url = request.path if not 'p' in request.GET else request.path + '?p=' + request.GET['p']
            return HttpResponseRedirect(url)
    
    # Check jmol mode.
    mode = request.session['jmol'] if 'jmol' in request.session else 'JAVA'
        
    # Set initial protein if requested
    initialProtein, initialHomodimer = False, None
    if 'p' in request.GET:
        initialProtein = int(request.GET['p'][1:])
        initialHomodimer = True if request.GET['p'][0] == 'h' else False
    curmut, curdom = None, None
    
    # Get protein and mutation from url request.
    currentIDs = request.path.split('/') # Job[2], Mut[3]
    job = currentIDs[2]
    iden, mut = getPnM(currentIDs[3])
    returnUrl = 'http://%s/result/%s/' % (request.get_host(), job)
    mutNum = int(mut[1:-1])

    # Get the mutation information or send back to main job URL.
    jtom = JobToMut.objects.filter(mut__mut=mut, inputIdentifier=iden, job_id=job)
    if len(jtom) != 1:
        return HttpResponseRedirect(returnUrl)
    m = jtom[0].mut
    j = Job.objects.get(jobID=job)
    if m.status != 'done':
        # Mutation is not done.
        return HttpResponseRedirect(returnUrl)
    
    loadEverything = True if m.affectedType != 'NO' else False
    
    # Load structure data if mutation was successful.
    intmuts = []
    inCore = True if m.affectedType == 'CO' or m.affectedType == 'NO' else False
    data = getResultData(jtom[0])
    
    if loadEverything:
        if data.realMutErr == 'DNE':
            return render(request, 'result2.html', {'url': returnUrl,
                                                    'current': 'result2',
                                                    'job': j,
                                                    'data': data,
                                                    'dbError': True})
        
        # Create pdb folder if not accessed before.
        pdbpath = os.path.join(settings.SAVE_PATH, job, currentIDs[3])
        if not os.path.exists(pdbpath):
            try:
                original_umask = os.umask(0)
                os.makedirs(pdbpath, 0777)
            finally:
                os.umask(original_umask)
        fileError = False
        
        # CORE.
        if inCore:
            # Transfer PDBs if not done before.
            copyfrom = os.path.join(settings.DB_PATH, 
                                 data.realMut[0].model.template.domain.data_path)
            if not os.path.exists(os.path.join(pdbpath, 'wt.pdb')):
                try:
                    copyfile(os.path.join(copyfrom, data.realMut[0].model_filename_wt), 
                             os.path.join(pdbpath, 'wt.pdb'))
                except Exception as e:
                    fileError = e
            if not os.path.exists(os.path.join(pdbpath, 'mut.pdb')):
                try:
                    copyfile(os.path.join(copyfrom, data.realMut[0].model_filename_mut), 
                             os.path.join(pdbpath, 'mut.pdb'))
                except Exception as e:
                    fileError = e
        # INTERFACE.
        else:
            doneInt, toRemove = [], []
            for i, mu in enumerate(data.realMut):
                # Get interacting domain.
                chain = 2 if mu.findChain() == 1 else 1
                d = mu.model.template.domain.getdomain(chain)
                
                # Check for dublicates. Remove the last one. 
                # This is a quick and dirty fix and should be fixed to pick 
                # the highest sequence identity.
                dubkey = '%s.%s.%d' % (m.protein, m.mut, d.id)
                if dubkey in doneInt:
                    toRemove.append(i)
                    continue
                else:
                    doneInt.append(dubkey)
                
                intmuts.append({'mut': mu,
                                'domain': d})
                # Transfer PDBs if not done before.
                copyfrom = os.path.join(settings.DB_PATH, 
                                     mu.model.template.domain.data_path)
                copyto = os.path.join(pdbpath, str(d.id))
                if not os.path.exists(copyto + 'wt.pdb'):
                    try:
                        copyfile(os.path.join(copyfrom, mu.model_filename_wt), 
                                 copyto + 'wt.pdb')
                    except Exception as e:
                        fileError = e
                if not os.path.exists(copyto + 'mut.pdb'):
                    try:
                        copyfile(os.path.join(copyfrom, mu.model_filename_mut), 
                                 copyto + 'mut.pdb')
                    except Exception as e:
                        fileError = e
        
            for rem in toRemove:
                data.realMut.remove(data.realMut[rem])
                
        # Show error page if database fetching failed.
        if fileError:
            # Could not read mutation from database. Return error.
            return render(request, 'result2.html', {'url': returnUrl,
                                                    'current': 'result2',
                                                    'job': j,
                                                    'data': data,
                                                    'dbError': True})
            
        p = data.realMut[0].protein
    # Load domains if mutation failed.
    elif not loadEverything:
        p = Protein.objects.using('uniprot').get(id=m.protein)
    
    pSize = len(p.seq) + 0.0

    # Get domain information.
    barSize = 868 if inCore else 590
    border = 1
    mutLineSize = 2
    mutDescSize = 70
    ds, domainName, proteinToDomainID = [], '', {}
    for idx, prot in enumerate([p] + ([mu['domain'].protein for mu in intmuts] if intmuts else [])):

        pds = Domain.objects.using('data').filter(protein_id=prot.id)
        
        # Check if homodimer with self.
        homodimer = True if prot == p else False
        
        for didx, pd in enumerate(pds):
            # Get domain definitions.
            defs = pd.getdefs(1)
            defstart = int(defs.split(':')[0])
            defend = int(defs.split(':')[1])
            dpSize = len(prot.seq) + 0.0
            pxSize = (defend - defstart) / dpSize * barSize - border * 2
            if pxSize < 0:
                pxSize = 0

            # If this is not an interaction.
            if not idx:
                # Color if mutaiton is in domain.
                index = 0
                isInDomain = True if defstart <= mutNum and defend >= mutNum else False
                if isInDomain:
                    domainName = pd.name
                
            # If this is an interaction.
            else:
                # Check if protein is already in list.
                if not didx:
                    notUnique = proteinToDomainID[prot.id] if prot.id in proteinToDomainID else False
                    if not notUnique:
                        proteinToDomainID[prot.id] = intmuts[idx - 1]['domain'].id
                    # Get chains for coloring.
                    chain = 1 if intmuts[idx - 1]['mut'].findChain() == 1 else 2
                    chainself = intmuts[idx - 1]['mut'].model.getchain(chain)
                    chaininac = intmuts[idx - 1]['mut'].model.getchain(1 if chain == 2 else 2)
                    # Get mutation info.
                    seqid = intmuts[idx - 1]['mut'].model.template.getsequenceidentity(chain)
                    dopescore = intmuts[idx - 1]['mut'].model.dope_score
                    dgwt = intmuts[idx - 1]['mut'].dGwt()
                    dgmut = intmuts[idx - 1]['mut'].dGmut()
                    ddg = intmuts[idx - 1]['mut'].getddG()
                    pdbmutnum = intmuts[idx - 1]['mut'].pdb_mut[1:-1]
                
                # Color if interacting with protein 1.
                index = intmuts[idx - 1]['domain'].id
                isInDomain = True if index == pd.id else False

                
            # Decrease domain name if it does not fit.
            if len(pd.name) * 7 < pxSize:
                dname = pd.name
                dpopup = ''
            elif 14 < pxSize:
                dname = pd.name[:max(int(pxSize/7)-2, 0)] + '..'
                dpopup = pd.name
            else:
                dname = ''
                dpopup = pd.name

            # Save domain info in list.
            # <i>, name, popup, pxstart, pxsize, start, end, status, psize.
            if not didx:
                ds.append([])
            try:
                protName = HGNCIdentifier.objects.using('uniprot').get(identifierType='HGNC_genename', uniprotID=prot.id)
            except HGNCIdentifier.DoesNotExist:
                try:
                    protName = UniprotIdentifier.objects.using('uniprot').get(identifierType='GeneWiki', uniprotID=prot.id)
                except (UniprotIdentifier.DoesNotExist, UniprotIdentifier.MultipleObjectsReturned):
                    protName = prot.name.split('_')[0]
            ds[idx].append([index, dname, dpopup, int(defstart / dpSize * barSize),
                            int(pxSize), defstart, defend, isInDomain, 
                            int(dpSize), prot.id, prot.desc, 
                            homodimer if idx else None,
                            chainself if idx and not didx else None, 
                            chaininac if idx and not didx else None,
                            notUnique if idx and not didx else None,
                            protName,
                            seqid if idx and not didx else None,
                            dopescore if idx and not didx else None,
                            dgwt if idx and not didx else None,
                            dgmut if idx and not didx else None,
                            ddg if idx and not didx else None,
                            pdbmutnum if idx and not didx else None])
            #if prot.name.split('_')[0] == 'UBC':
                #o += prot.name.split('_')[0] + ', '
            if pd.id == initialProtein and \
                    intmuts[idx - 1]['mut'].model.template.domain.getdomain(1 if chain == 2 else 2).id == initialProtein:
                curdom = ds[idx]
                curmut = intmuts[idx - 1]['mut']
                curmut.seqid = seqid
    pxMutnum = mutNum / pSize * barSize - mutLineSize/2
    if pxMutnum < 0:
            pxMutnum = 0
    if not curmut:
        curmut = data.realMut[0] if inCore else data.realMut[1]
        curdom = None if inCore else ds[1]
    
    if loadEverything:
        if not '[' in curmut.pdb_mut:
            pdbMutNum = int(curmut.pdb_mut[1:-1])
        else:
            pdbMutNum = int(curmut.pdb_mut[2:-2])
    else:
        data = {'inputIdentifier': iden, 
                'mut': {'mut': mut, 'desc': p.desc}}

    # Get the domains interacting.
    d2 = None
    if curdom:
        for dom in curdom:
            if dom[7]:
                d2 = dom
    for dom in ds[0]:
        if dom[7]:
            d1 = dom
            
    # Get domain interaction values for 2dbar.
    if d2:
        # Set start and end for each domain.
        d1s, d1e = d1[3], d1[3] + d1[4]
        d2s, d2e = d2[3], d2[3] + d2[4]
        # Find width of overlap/space.
        midleft = min(max(d1s, d2s), min(d1e, d2e))
        midright = max(max(d1s, d2s), min(d1e, d2e))
        midwidth = midright-midleft
        # Find width outside overlap/space.
        first_d = d1 if d1[3] <= d2[3] else d2
        last_d = d1 if d1[3] + d1[4] >= d2[3] + d2[4] else d2
        notfirst_d = d1 if first_d == d2 else d2
        # If complete overlap.
        if first_d == last_d:
            overlap = True
            leftwidth = notfirst_d[3] - first_d[3]
            rightwidth = (last_d[3] + last_d[4]) - (notfirst_d[3] + notfirst_d[4])
        # If overlap in one end.
        elif first_d[3] + first_d[4] > last_d[3]:  
            overlap = True
            leftwidth = last_d[3] - first_d[3]
            rightwidth = (last_d[3] + last_d[4]) - (first_d[3] + first_d[4])
        # If no overlap.
        else:
            overlap = False
            leftwidth = first_d[4]
            rightwidth = last_d[4]
        # Find which direction the overlap is going.
        leftside = 'down' if first_d == d1 else 'up'
        rightside = 'up' if last_d == d1 else 'down'
        midside = 'solid' if overlap else leftside
        # Calculate heights
        fullheight = 80
        if overlap:
            leftheight = rightheight = fullheight/2
            midtopheight = midbotheight = fullheight/4
        else:
            leftheight = (fullheight * first_d[4] / (midwidth + first_d[4])) / 2
            rightheight = (fullheight * last_d[4] / (midwidth + last_d[4])) / 2
            midtopheight = fullheight/2 - rightheight if leftside == 'down' else fullheight/2 - leftheight
            midbotheight = fullheight/2 - leftheight if leftside == 'down' else fullheight/2 - rightheight

    context = {
        'url': returnUrl,
        'current': 'result2',
        'job': j,
        'size': pSize,
        'domains': ds,
        'curdomain': curdom,
        'curmut': curmut,
        #'type': 'result',
        'barsize': barSize,
        'mutnum': pdbMutNum if loadEverything else 0,
        'mutnumdiff': mutNum - pdbMutNum if loadEverything else 0,
        'pxmutnum': pxMutnum,
        'pxmutdesc': pxMutnum - mutDescSize/2 + mutLineSize/2,
        'domainname': domainName,
        'wtpdb': '4BHB',
        'mutpdb': '4BHC_R37L',
        'selectrange': range(0,11),
        'data': data,
        'reverselabel': 'true' if m.mut[-1] == 'G' else 'false',
        'jmolmode': mode,
        'loadeverything': loadEverything,
        #'intmuts': intmuts,
        'inInt': not(inCore),
        'initialp': initialProtein,
        'initialh': initialHomodimer,
        'protein2dinac': {'full_height': fullheight if not inCore else 0,
                          'mid_left': midleft if not inCore else 0,
                          'mid_width': midwidth if not inCore else 0,
                          'left_width': leftwidth if not inCore else 0,
                          'right_width': rightwidth if not inCore else 0,
                          'mid_side': midside if not inCore else 0,
                          'left_side': leftside if not inCore else 0,
                          'right_side': rightside if not inCore else 0,
                          'left_height': leftheight if not inCore else 0,
                          'right_height': rightheight if not inCore else 0,
                          'mid_top_height': midtopheight if not inCore else 0,
                          'mid_bot_height': midbotheight if not inCore else 0,
                          'self_start': d1[3] if not inCore else 0,
                          'self_width': d1[4] if not inCore else 0} 
    }
#<i>, name, popup, pxstart, pxsize, start, end, status, psize    
    
    return render(request, 'result2.html', context)


def jsmolpopup(request):
    return render(request, 'jmolpopup.html', {})



def genericSite(request, site):

    context = {'this': site,
               'current': 'generic'}    
    context[site] = True
    
    if site == 'help':
        pass
    elif site == 'reference':
        pass
    elif site == 'contact':
        pass
    
      
    
    return render(request, 'generic.html', context)
    
#return render(request, 'test.html', {'msg': 'test'})