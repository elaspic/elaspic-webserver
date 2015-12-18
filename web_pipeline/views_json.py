from re import sub
from subprocess import Popen, PIPE
import json
import requests
from collections import defaultdict
from tempfile import NamedTemporaryFile

from Bio.PDB.PDBParser import PDBParser

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils import html
from django.conf import settings
from django.core.mail import EmailMessage

from web_pipeline.models import Job, JobToMut, Domain, Mutation, Imutation, Imodel
from web_pipeline.functions import isInvalidMut, getPnM, fetchProtein
from web_pipeline.filemanager import FileManager
from web_pipeline.tasks import cleanupServer

from web_pipeline.supl import pdb_template

#def prepareAllFiles(request):
#    if not request.GET:
#        raise Http404
#    if not 'j' in request.GET:
#        raise Http404
#    if not 'f' in request.GET:
#        raise Http404
#    jid = request.GET['j']
#    fold = request.GET['f']
#    pth = path.join(settings.SAVE_PATH, jid, fold)
#    respth = path.join(pth, 'job_' + jid + '_allresults.zip')
#    if path.exists(respth):
#        success = True
#    else:
#        try:
#            files = []
#            for aFile in walk(pth).next()[2]:
#                files.append(path.join(pth, aFile))
#            saveZip(respth, files)
#            success = True
#        except:
#            success = False
#    
#    return HttpResponse(json.dumps({'success': success}), content_type='application/json')




import logging

# Create logger to redirect output.
logName = "views_json"
logger = logging.getLogger(logName)
hdlr = logging.FileHandler('/home/kimadmin/mum/log/views_son.log')
hdlr.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)
logger.propagate = False


def rerunMut(request):
    if not request.GET:
        raise Http404
    if not 'm' or not 'j' in request.GET:
        raise Http404
    
    protein, mut = getPnM(request.GET['m'].upper())
    error = 0
    
    try:
        jtom = JobToMut.objects.get(job_id=request.GET['j'], inputIdentifier=protein, mut__mut=mut)
    except JobToMut.DoesNotExist:
        error = 1
    else:
        j = jtom.job
        j.isDone= False
        j.save()
        m = jtom.mut
        if not m.rerun:
            m.rerun = True
            m.save()
            # ##### Rerun pipeline #####
            # runPipelineWrapper.delay(m, j.jobID)
            # sleepabit.delay(5,10)
            data_in = [{
                'job_id': j.jobID,
                'job_email': j.email,
                'job_type': 'database',
                'protein_id': mut.protein,
                'mutations': mut.mut,
                'uniprot_domain_pair_ids': '',
            }]
            status = None
            n_tries = 0
            while (not status or status == 'error') and n_tries < 10:
                n_tries += 1
                r = requests.post('http://127.0.0.1:8000/elaspic/api/1.0/', json=data_in)
                status = r.json().get('status', None)

    return HttpResponse(json.dumps({'error': error}), content_type='application/json')


def dlFile(request):
    if not request.GET:
        raise Http404
    if not 'j' or not 'f' or not 'm' in request.GET:
        raise Http404
    
    fm = FileManager(jobID=request.GET['j'], muts=request.GET['m'].split(' '))

    response = HttpResponse(fm.makeFile(fileToMake=request.GET['f']), content_type=fm.type)
    
    del fm
    
    response['Content-Disposition'] = 'attachment; filename=' + request.GET['f']
    return response


def prepareDownloadFiles(request):
    ''' Used on result page to check for available files, prepared files in
        archives, and to return their file sizes. '''
    
    if not request.GET:
        raise Http404
    if not 'm' or not 'j' in request.GET:
        raise Http404
    
    files = ['simpleresults.txt', 'allresults.txt', 
             'wtmodels-ori.zip', 'wtmodels-opt.zip', 'mutmodels.zip',
             'alignments.zip', 'sequences.zip']

    jsonDict = {}
    fm = FileManager(jobID=request.GET['j'], muts=request.GET['m'].split(' '))
    
    for f in files:
        fm.makeFile(fileToMake=f)
        jsonDict[f.split('.')[0].replace("-", "")] = [fm.fileCount, fm.fileSize]
    
    del fm

    return HttpResponse(json.dumps(jsonDict), content_type='application/json')



def checkIfJobIsReady(request):

    if not request.POST:
        raise Http404
    if not 'j' in request.POST:
        raise Http404
    try:
        j = Job.objects.get(jobID=request.POST['j'])
    except Job.DoesNotExist:
        raise Http404
        
    staList, seqList, idenList = [], [], []
    for jm in j.jobtomut_set.all():
        staList.append(jm.mut.status)
        seqList.append(jm.mut.mut)
        idenList.append(jm.inputIdentifier)

    # TODO: job is ready when all mutations are ready
    jsonDict = {'done': j.isDone,
                'status': staList,
                'seq': seqList,
                'iden': idenList}
    
    return HttpResponse(json.dumps(jsonDict), content_type='application/json')


def _move_hetatm_to_hetatm_chain(chain, hetatm_chain, res):
    chain.detach_child(res.id)
    hetatm_res = res
    hetatm_res.id = (hetatm_res.id[0], len(hetatm_chain)+1, hetatm_res.id[2],)
    hetatm_chain.add(hetatm_res)

def _correct_methylated_lysines(res):
    lysine_atoms = ['N', 'CA', 'CB', 'CG', 'CD', 'CE', 'NZ', 'C', 'O']
    new_resname = 'LYS'
    new_resid = (' ', res.id[1], res.id[2])
    res.resname = new_resname
    res.id = new_resid
    atom_idx = 0
    while atom_idx < len(res):
        atom_id = res.child_list[atom_idx].id
        if atom_id not in lysine_atoms:
            res.detach_child(atom_id)
        else:
            atom_idx += 1


def uploadFile(request):
    
    if not request.FILES:
        raise Http404
    if not 'fileToUpload' in request.FILES:
        raise Http404
    
    myfile = request.FILES['fileToUpload']
    
    filetype = request.POST['filetype']
    
    if myfile.size > 5000000:
        jsonDict = {'msg': "File is too large (>5 MB)", 'error': 1}    
        return HttpResponse(json.dumps(jsonDict), content_type='application/json')
        

    try:
        process = Popen(['/usr/bin/file', '-i', myfile.temporary_file_path()], stdout=PIPE)
        stdout, stderr = process.communicate()
    
        if stdout.decode().split(' ')[1].split('/')[0] not in ('text', 'chemical'):
            msg =  "Uploaded file has to be raw text (not '{0}')".format(stdout.decode().split(' ')[1][:-1])
            jsonDict = {'msg': msg, 'error': 1}
            return HttpResponse(json.dumps(jsonDict), content_type='application/json')
            
        # Protein list upload.
        if filetype == 'prot':
            
            # Remove white-spaces and empty lines.
            lines = myfile.read().decode().split('\n')
            trimmedLines = []
            for idx, line in enumerate(lines):
                if idx >= 500:
                    break
                newline = sub(r'\s+', '', line)
                if newline:
                    trimmedLines.append(newline)
            msg = "\n".join(trimmedLines)

    except Exception:
        jsonDict = {'msg': "File could not be uploaded - try again", 'error': 1}
        return HttpResponse(json.dumps(jsonDict), content_type='application/json')
    
    
    if filetype == 'pdb':
        try:
        
            with NamedTemporaryFile(mode='w') as temp_fh:
                temp_fh.write(myfile.read().decode())
                temp_fh.flush()
                temp_fh.seek(0)

                structure = PDBParser(QUIET=True).get_structure('uploadedPDB', temp_fh.name)

            msg = sorted(pdb_template.get_structure_sequences(structure).items())
            
            print(len(msg[0][1]), len(msg[1][1]))
            
            if len(msg) < 1:
                jsonDict = {'msg': "PDB does not have any valid chains. ", 'error': 1}
                return HttpResponse(json.dumps(jsonDict), content_type='application/json')

        except Exception:
            jsonDict = {'msg': "PDB could not be parsed. ", 'error': 1}
            return HttpResponse(json.dumps(jsonDict), content_type='application/json')
            

        
    jsonDict = {'inputfile': myfile.name or 'uploadedFile',
                'msg': msg,
                'error': 0}    

    
    return HttpResponse(json.dumps(jsonDict), content_type='application/json')



def getProtein(request):
    
    
    #return HttpResponse(json.dumps({'r': [{'seq': 'AAAAAAAAAAAAAAAAAAAAAAAA'}], 'e': False}), content_type='application/json')    
    
    # Check if the site was reached with GET method.
    if not request.GET:
        raise Http404
    if not 'p' in request.GET:
        raise Http404
    
    # Parse requested input.
    inps = request.GET['p'].split()
    mutReq = True if 'm' in request.GET else False
    nameReq = True if 'n' in request.GET else False
    seqReq = True if 's' in request.GET else False
    domReq = True if 'd' in request.GET else False
    knownmutsReq = True if 'k' in request.GET else False
    errReq = True if 'e' in request.GET else False
    
    # Get all requested info from database.    
    output, done = [], set()
    for idx, inp in enumerate(inps):
        
        output.append({'error': False, 
                       'emsg': None,
                       'iden': inp})
        
        # Empty line.
        if inp == '':
            output[idx]['emsg'] = 'EMP'
            continue
                
        # Set input identifier
        if mutReq:
            protein, mut = getPnM(inp.upper())
        else:
            protein = inp
        if not protein:
            output[idx]['error'] = True
            output[idx]['emsg'] = 'SNX'
            continue
        
    
        # Get protein from database.
        p = fetchProtein(protein)
        if not p:
            output[idx]['error'] = True
            output[idx]['emsg'] = 'DNE'
            continue
        
        # Set basic info.
        output[idx]['prot'] = p.id
        output[idx]['nothuman'] = False if p.organismName == 'Homo sapiens' else True
            
        # Set sequence.
        if seqReq:
            output[idx]['seq'] = p.seq
                
        # Set gene name.
        if nameReq:
            output[idx]['desc'] = p.desc()
            output[idx]['gene'] = p.id #p.identifier_set.get(identifierType='geneName').identifierID
        
        # Set domains.
        if domReq:
            ds = list(Domain.objects.using('data').filter(protein_id=p.id))
            output[idx]['doms'], output[idx]['defs'] = [], []
            
            inacs = defaultdict(set)
            pidToName = {}

            for d in ds:
                output[idx]['doms'].append(d.getname(''))
                output[idx]['defs'].append(d.getdefs(1))
                
                # Set interactions.
                model1 = Imodel.objects.using('data').filter(template__domain__domain1=d)
                for m in model1:
                    if not m.aa1:
                        continue
                    pid = m.template.domain.domain2.protein_id
                    pidToName[pid] = m.template.domain.domain2.protein.getname()
                    inacs[pid] = set.union(inacs[pid], set(m.aa1.split(',')))
                model2 = Imodel.objects.using('data').filter(template__domain__domain2=d)
                for m in model2:
                    if not m.aa2:
                        continue
                    pid = m.template.domain.domain1.protein_id
                    pidToName[pid] = m.template.domain.domain1.protein.getname()
                    inacs[pid] = set.union(inacs[pid], set(m.aa2.split(',')))
            
            inacsum = defaultdict(int)
            for aas in inacs.values():
                for aa in aas:
                    inacsum[aa] += 1

            output[idx]['inacs'] = sorted([{'pid': k, 'prot': pidToName[k], 'aa': list(map(int,v))} for k,v in inacs.items()], key=lambda x: x['prot'])
            
            output[idx]['inacsum'] = inacsum

        
        # Set already known mutations for protein.
        if knownmutsReq:
            mdict = {}
            muts = list(Mutation.objects.using('data').filter(protein_id=p.id, mut_errors=None).exclude(ddG=None))
            imuts = list(Imutation.objects.using('data').filter(protein_id=p.id, mut_errors=None).exclude(ddG=None))
            
            for m in muts + imuts:
                chain = m.findChain()
                inac = m.getinacprot(chain) if m.__class__.__name__ == 'Imutation' else None
                isInt = inac.getname() if m.__class__.__name__ == 'Imutation' else None
                iId = inac.id if m.__class__.__name__ == 'Imutation' else None
                
                toAppend = {'i': isInt, 
                            'id': iId,
                            'm': m.mut, 
                            'd': '%0.3f' % m.ddG,
                            'dw': m.dGwt(),
                            'dm': m.dGmut(),
                            'si': m.model.template.getsequenceidentity(chain),
                            'sm': '%0.3f' % m.model.dope_score}
                if m.mut in mdict and mdict[m.mut][0]['i']:
                    mdict[m.mut].append(toAppend)
                else:
                    mdict[m.mut] = [toAppend]
            
            knMuts = {}

            for k in mdict:
                mnum = mdict[k][0]['m'][1:-1]
                knMuts.setdefault(mnum, list()).append(mdict[k])

            # Sort mutations
            for k in knMuts:
                knMuts[k] = sorted(knMuts[k], key=lambda x: x[0]['m'])

            #output[idx]['prot'] = str(knMuts['537'])
            output[idx]['known'] = knMuts

        
        # Set mutation.
        if mutReq:
            output[idx]['mut'] = mut
            output[idx]['muterr'] = isInvalidMut(mut, p.seq)
        
            # Check for duplicate.
            l = len(done)
            done.add(p.id + mut)
            if l == len(done):
                output[idx]['error'] = True
                output[idx]['emsg'] = 'DUP'
        
    # Create error lists.
    if errReq:
       
       # Save and count all errors.
        errDict = {'SNX': {}, 'DNE': {}, 'SLF': {},
                   'DUP': {}, 'SYN': {}, 'OOB': {}}
        good = []
        for prot in output:
            if prot['emsg'] == 'EMP':
                continue
            if prot['error']:
                idx = 'emsg'
            elif prot['muterr']:
                idx = 'muterr'
            else:
                good.append(prot['iden'])
                continue
            if not prot['iden'] in errDict[prot[idx]]:
                errDict[prot[idx]][prot['iden']] = 1
            else:
                errDict[prot[idx]][prot['iden']] += 1
        
        # Translate to list of format "PROT.MUT (1x)"
        errIdx = {'SNX': 0, 'DNE': 1, 'OOB': 2,
                  'SLF': 3, 'DUP': 4, 'SYN': 5}
        err = {'errors': [[],[],[],[],[],[]], 'header': [], 'eclass': [], 
               'good': good, 'title': False}
        for eidx in errDict:
            err['errors'].append([])
            for prot in errDict[eidx]:
                if errDict[eidx][prot] == 1:
                    err['errors'][errIdx[eidx]].append('<b>%s</b>' % prot)
                else:
                    err['errors'][errIdx[eidx]].append('<b>%s</b> (x%d)' % (prot, errDict[eidx][prot]))
        
        
        # Assign headeres to error lists.
        errLists = 0
        for idx, errls in enumerate(err['errors']):
            err['header'].append(None)
            err['eclass'].append(None)
            if len(errls) > 0:
                errLists += 1
                if len(errls) == 1:
                    if idx == 0:
                        title = 'There is a line with invalid syntax.'
                    elif idx == 1:
                        title = 'There is an unrecognized gene symbol.'
                    elif idx == 2:
                        title = 'There is an unrecognized protein residue.'
                    elif idx == 3:
                        title = 'There is a synonymous mutation.'
                    elif idx == 4:
                        title = 'There is a duplicated gene symbol.'
                    elif idx == 5:
                        title = 'There is a duplicated gene symbol.'
                else:
                    if idx == 0:
                        title = 'There are lines with invalid syntax.'
                    elif idx == 1:
                        title = 'There are unrecognized gene symbols.'
                    elif idx == 2:
                        title = 'There are unrecognized protein residues.'
                    elif idx == 3:
                        title = 'There are synonymous mutations.'
                    elif idx == 4:
                        title = 'There are duplicate gene symbols.'
                    elif idx == 5:
                        title = 'There are duplicate gene symbols.'
               
                if idx == 0:
                    header = 'Invalid syntax'
                    myclass = 'error'
                elif idx == 1:
                    header = 'Unrecognized gene symbols'
                    myclass = 'unknown'
                elif idx == 2:
                    header = 'Unrecognized protein residues'
                    myclass = 'unknown'
                elif idx == 3:
                    header = 'Synonymous mutations'
                    myclass = 'warning'
                elif idx == 4:
                    header = 'Duplicates'
                    myclass = 'warning'
                elif idx == 5:
                    header = 'Synonyms'
                    myclass = 'warning'
                    

                err['header'][idx] = '%s (%d):' % (header, len(errls))
                err['eclass'][idx] = myclass
        if errLists == 1:
            err['title'] = title
        if errLists > 1:
            err['title'] = 'There are multiple errors.'
    else:
        err = None

    # Return.
    return HttpResponse(json.dumps({'r': output, 'e': err}), 
                                          content_type='application/json')
    

def sendContactMail(request):
    
    # Check if the page was reached legitimately. 
    if not request.POST:
        raise Http404
    if not 'name' or not 'from' or not 'topic' or not 'msg' in request.POST:
        raise Http404
        
    from_email = request.POST['from']
    subject = 'ELASPIC: ' + request.POST['topic']
    
    message = '<i>From: ' + html.strip_tags(request.POST['name']) + '<br />'
    message += 'Email: ' + html.strip_tags(from_email) + '</i><br /><br />'
    message += 'Topic: <b>' + html.strip_tags(request.POST['topic']) + '</b><br /><br />'
    message += 'Message: <br /><b>'
    message += html.strip_tags(request.POST['msg']).replace('\n', '<br/>');
    message += '</b>';
    
    email = EmailMessage(subject, message, 'ELASPIC-webserver@kimlab.org', [a[1] for a in settings.ADMINS])
    email.headers = {'Reply-To': from_email, 'From': 'ELASPIC-webserver@kimlab.org'}
    email.content_subtype = "html"
    
    try:
        email.send()
    except Exception:
        error = True
        response = 'Sorry, there was an error with your request. Please try again.'   
    else:
        error = False
        response = 'Your message has been successfully sent. Allow us 2 business days to get back to you.'

    
    return HttpResponse(json.dumps({'response': response, 'error': error}), content_type='application/json')
    
def cleanup(request):
    cleanupServer.delay()
    return HttpResponseRedirect('/')
 
