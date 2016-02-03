from re import sub
from subprocess import Popen, PIPE
from os import path, mkdir
from shutil import copyfile
import json
import requests
from collections import defaultdict, Counter
from tempfile import NamedTemporaryFile
from random import randint
import pickle
import logging
import time

from Bio.PDB.PDBParser import PDBParser

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils import html
from django.conf import settings
from django.core.mail import EmailMessage

from mum.settings import DB_PATH

from web_pipeline.models import (
    Job, JobToMut, Mut, findInDatabase, get_protein_name,
    Protein, ProteinLocal,
    CoreModel, CoreModelLocal,
    CoreMutation, CoreMutationLocal,
    InterfaceModel, InterfaceModelLocal,
    InterfaceMutation, InterfaceMutationLocal
)
from web_pipeline.functions import isInvalidMut, getPnM, fetchProtein
from web_pipeline.filemanager import FileManager
from web_pipeline.cleanupmanager import CleanupManager

from web_pipeline.supl import pdb_template


# def prepareAllFiles(request):
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


# Create logger to redirect output.
logger = logging.getLogger(__name__)


def rerunMut(request):
    if not request.GET:
        raise Http404
    if not ('m' in request.GET) or not ('j' in request.GET):
        raise Http404

    protein, mut = getPnM(request.GET['m'].upper())
    error = 0

    try:
        jtom = JobToMut.objects.get(job_id=request.GET['j'], inputIdentifier=protein, mut__mut=mut)
    except JobToMut.DoesNotExist:
        error = 1
    else:
        j = jtom.job
        j.isDone = False
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
                'secret_key': settings.JOBSUBMITTER_SECRET_KEY,
            }]
            status = None
            n_tries = 0
            while (not status or status == 'error') and n_tries < 10:
                n_tries += 1
                r = requests.post('http://127.0.0.1:8000/elaspic/api/1.0/', json=data_in)
                status = r.json().get('status', None)

    return HttpResponse(json.dumps({'error': error}), content_type='application/json')


def dlFile(request):
    logger.debug("dlFile({})".format(request))
    if not request.GET:
        raise Http404
    if not ('j' in request.GET) or not ('f' in request.GET) or not ('m' in request.GET):
        raise Http404

    fm = FileManager(jobID=request.GET['j'], muts=request.GET['m'].split(' '))

    response = HttpResponse(fm.makeFile(fileToMake=request.GET['f']), content_type=fm.type)

    del fm

    response['Content-Disposition'] = 'attachment; filename=' + request.GET['f']
    return response


def prepareDownloadFiles(request):
    logger.debug("prepareDownloadFiles({})".format(request))
    ''' Used on result page to check for available files, prepared files in
        archives, and to return their file sizes. '''

    if not request.GET:
        raise Http404
    if not 'm' or not ('j' in request.GET):
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
    if not ('j' in request.POST):
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
    if not ('fileToUpload' in request.FILES):
        raise Http404

    myfile = request.FILES['fileToUpload']

    filetype = request.POST['filetype']
    randomID = ''

    if myfile.size > 10000000:
        jsonDict = {'msg': "File is too large (>10 MB)", 'error': 1}
        return HttpResponse(json.dumps(jsonDict), content_type='application/json')

    try:
        process = Popen(['/usr/bin/file', '-i', myfile.temporary_file_path()], stdout=PIPE)
        stdout, stderr = process.communicate()

        if stdout.decode().split(' ')[1].split('/')[0] not in ('text', 'chemical'):
            msg = (
                "Uploaded file has to be raw text (not '{0}')"
                .format(stdout.decode().split(' ')[1][:-1])
            )
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

                seq = sorted(pdb_template.get_structure_sequences(structure).items())

                if len(seq) < 1:
                    jsonDict = {'msg': "PDB does not have any valid chains. ", 'error': 1}
                    return HttpResponse(json.dumps(jsonDict), content_type='application/json')

                # Save uploaded pdb if it is valid.
                while True:
                    randomID = "%06x" % randint(1, 16777215)
                    user_path = path.join(DB_PATH, 'user_input', randomID)
                    if (Job.objects.filter(jobID=randomID).count() == 0 and not
                            path.exists(user_path)):
                        break
                if not path.exists(user_path):
                    mkdir(user_path)
                copyfile(temp_fh.name, path.join(user_path, 'input.pdb'))
            with open(path.join(user_path, 'pdb_parsed.pickle'), 'bw') as f:
                f.write(pickle.dumps(seq))

            msg = seq

        except Exception as e:
            print(e)
            jsonDict = {'msg': "PDB could not be parsed. ", 'error': 1}
            return HttpResponse(json.dumps(jsonDict), content_type='application/json')

    jsonDict = {'inputfile': myfile.name or 'uploadedFile',
                'userpath': randomID,
                'msg': msg,
                'error': 0}

    return HttpResponse(json.dumps(jsonDict), content_type='application/json')


def getProtein(request):
    logger.debug("getProtein({})".format(request))

    # return HttpResponse(
    #    json.dumps({'r': [{'seq': 'AAAAAAAAAAAAAAAAAAAAAAAA'}], 'e': False}),
    #    content_type='application/json')

    # Check if the site was reached with GET method.
    if not request.GET:
        raise Http404
    if not ('p' in request.GET):
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
        output[idx]['nothuman'] = False if p.organism_name == 'Homo sapiens' else True

        # Set sequence.
        if seqReq:
            output[idx]['seq'] = p.seq

        # Set gene name.
        if nameReq:
            output[idx]['desc'] = p.desc()
            # p.identifier_set.get(identifierType='geneName').identifierID
            output[idx]['gene'] = p.id

        logger.debug("Intro output: {}".format(output))

        # Set domains.
        if domReq or knownmutsReq:
            all_interface_models = set()
            ds = list(CoreModel.objects.filter(protein_id=p.id))
            output[idx]['doms'], output[idx]['defs'] = [], []
            domain_range_all = set()

            inacs = defaultdict(set)
            pidToName = {}

            logger.debug('Going over all domains and interactions...')
            for d in ds:
                output[idx]['doms'].append(d.getname(''))
                defs = d.getdefs(1)
                output[idx]['defs'].append(defs)
                domain_range = set(range(int(defs.split(':')[0]), int(defs.split(':')[1]) + 1))
                domain_range_all.update(domain_range)

                # Set interactions.
                model1 = (
                    InterfaceModel.objects.filter(domain1=d)
                    .exclude(aa1__isnull=True).exclude(aa1__exact='').exclude(aa1__exact=',')
                )
                for m in model1:
                    partner_protein_id, partner_protein_name = m.protein_id_2, m.get_protein_name(2)
                    pidToName[partner_protein_id] = partner_protein_name
                    inacs[partner_protein_id] = set.union(inacs[partner_protein_id], set(m.aa1.split(',')))
                    all_interface_models.add((m, partner_protein_id, partner_protein_name))
                model2 = (
                    InterfaceModel.objects.filter(domain2=d)
                    .exclude(aa2__isnull=True).exclude(aa2__exact='').exclude(aa2__exact=',')
                )
                for m in model2:
                    partner_protein_id, partner_protein_name = m.protein_id_1, m.get_protein_name(1)
                    pidToName[partner_protein_id] = partner_protein_name
                    inacs[partner_protein_id] = set.union(inacs[partner_protein_id], set(m.aa2.split(',')))
                    all_interface_models.add((m, partner_protein_id, partner_protein_name))

            inacsum = defaultdict(int)
            for aas in inacs.values():
                for aa in aas:
                    inacsum[aa] += 1

            output[idx]['inacs'] = sorted(
                [{'pid': k, 'prot': pidToName[k], 'aa': list(map(int, v))}
                 for k, v in inacs.items()],
                key=lambda x: x['prot']
            )

            output[idx]['inacsum'] = inacsum
        logger.debug('Done going over all domains and interactions!')
        logger.debug("output: {}".format(output))

        # Set already known mutations for protein.
        logger.debug('knownmutsReq')
        if knownmutsReq:
            mdict = {}
            logger.debug('querying mutations...')
            # muts = (
            #     list(CoreMutation.objects
            #          .filter(protein_id=p.id, mut_errors=None).exclude(ddG=None)) +
            #     list(InterfaceMutation.objects
            #          .filter(protein_id=p.id, mut_errors=None).exclude(ddG=None))
            # )
            muts = (
                [(mut, None, None)
                 for model in ds
                 for mut in model.muts.exclude(ddG=None)
                 if int(mut.mut[1:-1]) in domain_range_all] +
                [(mut, partner_protein_id, partner_protein_name)
                 for (model, partner_protein_id, partner_protein_name) in all_interface_models
                 for mut in model.muts.filter(protein_id=p.id).exclude(ddG=None)
                 if int(mut.mut[1:-1]) in domain_range_all]
            )
            logger.debug("muts: '{}'".format(muts))
            logger.debug('done querying mutations...')

            mut_dbs = findInDatabase([m[0].mut for m in muts], p.id)

            logger.debug("Done 'findInDatabase'")

            # Skip core mutations not in any database.
            muts = [
                m for m in muts
                if ((isinstance(m[0], (CoreMutationLocal, InterfaceMutationLocal))) or
                    (isinstance(m[0], (CoreMutation, InterfaceMutation)) and len(mut_dbs[m[0].mut])))
            ]
            # If still > 100 mutations, keep residues with the largest number of mutants
            MAX_NUM_MUTATIONS = 100
            if len(muts) > MAX_NUM_MUTATIONS:
                mutated_residue_counts = Counter([m[0].mut[:-1] for m in muts])
                most_common_mutated_residues = {x[0] for x in mutated_residue_counts.most_common(MAX_NUM_MUTATIONS)}
                muts = [m for m in muts if m[0].mut[:-1] in most_common_mutated_residues]

            for m_tuple in muts:
                m, partner_protein_id, partner_protein_name = m_tuple
                chain = m.findChain()
                isInt = partner_protein_name
                iId = partner_protein_id
                
                mut_dbs_html = ''
                if mut_dbs[m.mut]:
                    mut_dbs_html = (
                        'Mutation in database' + ('s' if len(mut_dbs[m.mut]) > 1 else '') + ': '
                    )
                    for i, db in enumerate(mut_dbs[m.mut]):
                        if i:
                            mut_dbs_html += ' ,'
                        mut_dbs_html += (
                            '<a target="_blank" href="' + db['url'] + '">' + db['name'] + '</a>'
                        )
                else:
                    mut_dbs_html = 'Mutation run by user'

                toAppend = {'i': isInt,
                            'id': iId,
                            'm': m.mut,
                            'd': '%0.3f' % m.ddG,
                            'dw': m.dGwt(),
                            'dm': m.dGmut(),
                            'si': m.model.getsequenceidentity(chain),
                            'sm': '%0.3f' % m.model.dope_score,
                            'db': mut_dbs_html}
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
                knMuts[k] = sorted(knMuts[k], key=lambda x: int(x[0]['m'][1:-1]))

            # output[idx]['prot'] = str(knMuts['537'])
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
        err = {'errors': [[], [], [], [], [], []], 'header': [], 'eclass': [],
               'good': good, 'title': False}
        for eidx in errDict:
            err['errors'].append([])
            for prot in errDict[eidx]:
                if errDict[eidx][prot] == 1:
                    err['errors'][errIdx[eidx]].append('<b>%s</b>' % prot)
                else:
                    err['errors'][errIdx[eidx]].append(
                        '<b>%s</b> (x%d)' % (prot, errDict[eidx][prot]))

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

    # Return
    logger.debug("output: {}".format(output))
    logger.debug("err: {}".format(err))
    return HttpResponse(json.dumps({'r': output, 'e': err}), content_type='application/json')


def sendContactMail(request):
    # Check if the page was reached legitimately.
    if not request.POST:
        raise Http404
    if not any(x in request.POST for x in ['name', 'from', 'topic', 'msg']):
        raise Http404

    from_email = request.POST['from']
    subject = 'ELASPIC: ' + request.POST['topic']

    message = '<i>From: ' + html.strip_tags(request.POST['name']) + '<br />'
    message += 'Email: ' + html.strip_tags(from_email) + '</i><br /><br />'
    message += 'Topic: <b>' + html.strip_tags(request.POST['topic']) + '</b><br /><br />'
    message += 'Message: <br /><b>'
    message += html.strip_tags(request.POST['msg']).replace('\n', '<br/>')
    message += '</b>'

    email = EmailMessage(
        subject, message, 'ELASPIC-webserver@kimlab.org', [a[1] for a in settings.ADMINS]
    )
    email.headers = {'Reply-To': from_email, 'From': 'ELASPIC-webserver@kimlab.org'}
    email.content_subtype = "html"

    try:
        email.send()
    except Exception:
        error = True
        response = 'Sorry, there was an error with your request. Please try again.'
    else:
        error = False
        response = (
            'Your message has been successfully sent. '
            'Allow us 2 business days to get back to you.'
        )
    return HttpResponse(
        json.dumps({'response': response, 'error': error}), content_type='application/json')


def cleanupServer():

    c = CleanupManager()

    # Remove jobs last visited too long ago.
    c.removeOldJobs()

#    c.checkForStalledMuts()

    # Restart stalled jobs, and delete orphan mutations still running/queued.
#    m_runAgain = c.checkForStalledJobs()
#    for m in m_runAgain:
#        runPipelineWrapper.delay(m[0], m[1])

    # Send crash logs to admins.
    c.sendCrashLogs()


def cleanup(request):
    # TODO: Send this to a different thread
    cleanupServer()
    return HttpResponseRedirect('/')
