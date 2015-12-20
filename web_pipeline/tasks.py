from __future__ import absolute_import


import shutil
import os
import traceback
import re
import time
import logging
from tempfile import NamedTemporaryFile, mkdtemp
from time import sleep
from random import randint

from celery.exceptions import SoftTimeLimitExceeded

from django.conf import settings
from django.utils.timezone import now, localtime
from django.template import Context
from django.template.loader import get_template

from mum.celeryapp import app
from web_pipeline.functions import checkForCompletion
from web_pipeline.models import Mutation, Imutation
from web_pipeline.cleanupmanager import CleanupManager

os.environ['MPLCONFIGDIR'] = mkdtemp()
from elaspic.pipeline import Pipeline
from web_pipeline.elaspic_socket_client import JobSubmitter
#from web_pipeline import jobsubmitter


@app.task
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

#    return len(m_runAgain)

@app.task
def sleepabit(a=5, b=10):

    sleepFor = randint(a, b)
    print("Will now sleep for %d seconds." % sleepFor)
    sleep(sleepFor)
    print("Done sleeping!")

    return 1


def _run_pipeline_locally(mutation, logger):
    pipeline = Pipeline(settings.ELASPIC_CONFIG_FILENAME, logger=logger)
    logger.info('----- Running: %s.%s -----' % (mutation.protein, mutation.mut))
    pipeline(mutation.protein, mutation.mut, run_type=5)


def _run_pipeline_remotely_old(mutation, logger):
    js = JobSubmitter(logger=logger)

    logger.debug("uniprot_id: {}, mutations: {}".format(mutation.protein, mutation.mut))
    js.submitjob(mutation.protein, mutation.mut)

    time.sleep(5)
    output_dict = js.check_progress(mutation.protein, mutation.mut)
    logger.debug('output_dict: {}'.format(output_dict))
    while not output_dict.get('status') == "Done":
        time.sleep(60)
        output_dict.update(js.check_progress(mutation.protein, mutation.mut))
    #TODO: There are better ways to handle job_ids (read files in finished/ folder),
    #but we don't need them for now...
    return output_dict


def _run_pipeline_remotely(mutation, logger):
    import requests
    url = 'http://192.168.6.201:8890/elaspic/api/v1.0/submitjob'

    logger.debug("uniprot_id: {}, mutations: {}".format(mutation.protein, mutation.mut))
    r = requests.post(url, {'uniprot_id': mutation.protein, 'mutations': mutation.mut})
    logger.debug('post response: {}'.format(r.json()))

    time.sleep(5)
    r = requests.get(url, {'uniprot_id': mutation.protein, 'mutations': mutation.mut})
    logger.debug('output_dict: {}'.format(r.json()))
    while True:
        if r.json().get('message') == 'Internal Server Error':
            break
        if r.json().get(mutation.mut, {}).get('result'):
            break
        if r.json().get(mutation.mut, {}).get('status') == 'Done':
            break
        time.sleep(60)
        r = requests.get(url, {'uniprot_id': mutation.protein, 'mutations': mutation.mut})
        logger.debug('output_dict: {}'.format(r.json()))
    return r.json()


#@app.task(rate_limit='10/m', max_retries=2)
@app.task
def runPipelineWrapper(mutation, jid):

    # Set mutation status as running.
    if not mutation.rerun:
        mutation.status = 'running'
    else:
        mutation.rerun = 2
    mutation.save()

    # Change current folder to pipeline code.
    #~ tempDir = "elaspic_%s_%s_%s/" % (jid, mutation.protein, mutation.mut)
    #~ pipelineDir = os.path.join(settings.PROJECT_ROOT, 'pipeline/code/')
    #~ os.chdir(pipelineDir)
    #~
    # Create temp config file.
    #~ t = get_template('configTemp.ini')
    #~ c = Context({'tempDir': tempDir,
                 #~ 'debug': str(settings.PIPELINE_DEBUG),
                 #~ 'dbPath': str(settings.DB_PATH),
                 #~ 'blastDbPath': str(settings.BLAST_DB_PATH),
                 #~ 'pdbPath': str(settings.PDB_PATH),
                 #~ 'binPath': str(settings.BIN_PATH),
                 #~ 'dbFile': str(settings.DB_FILE)})
    #~ tf = NamedTemporaryFile()
    #~ tf.write(t.render(c))
    #~ tf.flush()


    # Set environment variables from ~/.bashrc.
    #~ old_env = os.environ
    #~ with open(os.path.join(settings.HOME_PATH, '.bashrc')) as f:
        #~ for l in f:
            #~ if l[:6] != 'export':
                #~ continue
            #~ # Get all path variables to set.
            #~ envVar, envPath = re.match(r'^export (.+?)="?(.+?)"?$', l[:-1]).groups()
            #~ # Extract %SOME_VAR from paths and substitute with %s.
            #~ envPathVars = re.findall(r'\$[0-9A-Z_]*', envPath)
            #~ envPath = re.sub(r'\$[0-9A-Z_]*', '%s', envPath)
            #~ # Insert current environmental variables into %s.
            #~ os.environ[envVar] = envPath % tuple([os.environ.get(l[1:]) or '' for l in envPathVars])

    args_list = [{
        'job_type': 'database',
        'protein_id': mutation.protein,
        'mutations': mutation.mut,
        'uniprot_domain_pair_ids': '',
    }]

    # Create logger to redirect output.
    logName = "%s_%s_%s" % (localtime(now()).strftime('%Y-%m-%d_%H.%M.%S'),
                            mutation.protein, mutation.mut)
    logFile = NamedTemporaryFile()
    logger = logging.getLogger(logName)
    hdlr = logging.FileHandler(logFile.name)
    hdlr.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    exitCode = -1

    try:
        logger.info("mutation: {}".format(mutation))

        ### Run pipeline ###
        #_run_pipeline_locally(mutation, logger)
#        output_dict = _run_pipeline_remotely(mutation, logger)
        jobsubmitter.main(args_list)
#        logger.debug("Saving job ids to the database...")
#        mutation.provean_job_id = output_dict.get('sequence', {}).get('job_id')
#        mutation.model_job_id = output_dict.get('sequence', {}).get('job_id')
#        mutation.mutation_job_id = output_dict.get('sequence', {}).get('job_id')

    except SoftTimeLimitExceeded:
        # Out of time. Cleanup!
        mutation.status = 'error'
        mutation.affectedType = ''
        mutation.error = '3: OUTATIME'
        exitCode = 3

    except Exception as e:
        print('The following exception occured!\n{}'.format(e))

        # Other unknown exception.
        mutation.status = 'error'
        mutation.affectedType = ''
        mutation.error = '2: PIPELINECRASH: %s' % str(e)

        # Save crashlog.
        trace = traceback.format_exc()
        logger.error(trace)
        logFile.flush()
        shutil.copy(logFile.name, os.path.join(settings.CRASH_LOG_PATH, logName + '.log'))

        exitCode = 2

    else:
        # Fetch completed mutations.
        mut = list(Mutation.objects.using('data').filter(protein_id=mutation.protein, mut=mutation.mut))
        imut = list(Imutation.objects.using('data').filter(protein_id=mutation.protein, mut=mutation.mut))

        # Check if an error occoured.
        coreOrInt, muts = ('IN', imut) if imut else ('CO', mut)
        if mut + imut:
            mutErrs = None if any([not(m.mut_errors) for m in muts]) else '1: ' + ', '.join([str(m.mut_errors) for m in muts])
            ddGmissing = any([not(m.ddG) for m in muts])
            # Update mutation with data.
            if mutErrs or ddGmissing:
                exitCode = 1
                mutation.status = 'error'
                mutation.error = mutErrs or '1: ddG not calculated'
            else:
                mutation.error = None
                mutation.status = 'done'
                mutation.affectedType = coreOrInt
                exitCode = 0
        else:
            # Check if mutation falls out of domain.
#            try:
#                inDomain = False
#                domains = list(Domain.objects.using('data').filter(protein_id=mutation.protein))
#                mut_num = int(mutation.mut[1:-1])
#                for d in domains:
#                    d_start, d_end = d.getdefs().split(':')
#                    d_start, d_end = int(d_start), int(d_end)
#                    if mut_num >= d_start and mut_num <= d_end:
#                        inDomain = True
#                        break
#            except Exception:
#                exitCode = 2
#                mutation.status = 'error'
#                mutation.error = '2: Database error'
#            else:
            exitCode = 6
            mutation.status = 'done'
            mutation.error = None
            mutation.affectedType = 'NO'


    finally:

        # Fail-safe in case of sys.exit() or some other dangerous stuff is
        # called within the pipeline.
        if exitCode == -1:
            mutation.status = 'error'
            mutation.error = '2: PIPELINECRASH: EXIT STATUS 4'

        # (Save and) Remove logger
        if settings.DEBUG:
            logFile.flush()
            shutil.copy(logFile.name, os.path.join(settings.ELASPIC_LOG_PATH, logName + '.log'))
        logger.handlers = []
        logFile.close()

        # Set current working directory and environment back to default.
        os.chdir(os.path.join(settings.PROJECT_ROOT, '..'))
        #~ os.environ = old_env

        # Save mutation.
        mutation.dateFinished = now()
        mutation.rerun = False
        mutation.save()

         # If all mutations in job are done, then set job as done.
        checkForCompletion(mutation.jobs.all())

        # Delete temp folders.
        try:
            shutil.rmtree(os.environ['MPLCONFIGDIR'])
            os.environ['MPLCONFIGDIR'] = ''
        except Exception:
            pass
        ## AS commented out
#        try:
#            shutil.rmtree('/tmp/' + tempDir)
#        except Exception:
#            pass

        # Return.
        # 0: Complete without errors.
        # 1: Complete with errors.
        # 2: Pipeline crash (log saved).
        # 3: Out of time, set in settings.py.
        # 4: Unknown error, not logged.
        # 5: Blacklisted protein.
        return exitCode if exitCode == -1 else 4




#@app.task(rate_limit='10/m', max_retries=2)
def runPipelineWrapperAll(mutations, jid):
    """
    If there are multiple mutations in the same protein, submit them together.
    """
    if not isinstance(mutations, list):
        mutations = [mutations]

    # Group mutations
    args_list = [
        {
            'job_type': 'database',
            'protein_id': mutation.protein,
            'mutations': mutation.mut,
            'uniprot_domain_pair_ids': '',
        } for mutation in mutations
    ]

    # Set mutation status as running.
    for mutation in mutations:
        if not mutation.rerun:
            mutation.status = 'running'
        else:
            mutation.rerun = 2
        mutation.save()


    # Create logger to redirect output.
    logName = "%s" % localtime(now()).strftime('%Y-%m-%d_%H.%M.%S')
    logFile = NamedTemporaryFile()
    logger = logging.getLogger(logName)
    hdlr = logging.FileHandler(logFile.name)
    hdlr.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    exitCode = -1


    logger.info('running runPipelineWrapperAll...')
    logger.info("mutations: {}".format(mutations))
    logger.info("args_list: {}".format(args_list))


    try:

        ### Run pipeline ###
        #_run_pipeline_locally(mutation, logger)
        jobsubmitter.main(args_list)
        # mutation_dict_output = _run_pipeline_remotely(mutation_dict, logger)

#        for mutation in mutations:
#            mutation.provean_job_id = mutation_dict_output[mutation.protein].get('provean_job_id')
#            mutation.model_job_id = mutation_dict_output[mutation.protein].get('model_job_id')
#            mutation.mutation_job_id = mutation_dict_output[mutation.protein].get('mutation_job_id')

        # Save logs if we're debugging
        if settings.DEBUG:
            logFile.flush()
            shutil.copy(logFile.name, os.path.join(settings.ELASPIC_LOG_PATH, logName + '.log'))

    except SoftTimeLimitExceeded:
        # Out of time. Cleanup!
        for mutation in mutations:
            mutation.status = 'error'
            mutation.affectedType = ''
            mutation.error = '3: OUTATIME'
            exitCode = 3

    except Exception as e:
        print('The following exception occured!\n{}'.format(e))
        # Other unknown exception.
        for mutation in mutations:
            mutation.status = 'error'
            mutation.affectedType = ''
            mutation.error = '2: PIPELINECRASH: %s' % str(e)

        # Save crashlog.
        trace = traceback.format_exc()
        logger.error(trace)
        logFile.flush()
        shutil.copy(logFile.name, os.path.join(settings.CRASH_LOG_PATH, logName + '.log'))

        exitCode = 2

    else:
        # Fetch completed mutations.
        logger.debug("Going over every mutation to check if it's been calculcated correctly...")
        for mutation in mutations:
            mut = list(Mutation.objects.using('data').filter(protein_id=mutation.protein, mut=mutation.mut))
            imut = list(Imutation.objects.using('data').filter(protein_id=mutation.protein, mut=mutation.mut))

            # Check if an error occoured.
            coreOrInt, muts = ('IN', imut) if imut else ('CO', mut)
            if mut + imut:
                mutErrs = None if any([not(m.mut_errors) for m in muts]) else '1: ' + ', '.join([str(m.mut_errors) for m in muts])
                ddGmissing = any([not(m.ddG) for m in muts])
                # Update mutation with data.
                if mutErrs or ddGmissing:
                    exitCode = 1
                    mutation.status = 'error'
                    mutation.error = mutErrs or '1: ddG not calculated'
                else:
                    mutation.error = None
                    mutation.status = 'done'
                    mutation.affectedType = coreOrInt
                    exitCode = 0
            else:
                exitCode = 6
                mutation.status = 'done'
                mutation.error = None
                mutation.affectedType = 'NO'

        logger.debug('mutations: {}'.format(mutations))

    finally:
        logger.debug("Check that everything is complete and send out emails...")
        for mutation in mutations:
            logger.debug("mutation: {}".format(mutation))
            # Fail-safe in case of sys.exit() or some other dangerous stuff is
            # called within the pipeline.
            if exitCode == -1:
                mutation.status = 'error'
                mutation.error = '2: PIPELINECRASH: EXIT STATUS 4'
            logger.debug("Exit code: {}".format(exitCode))

            # Save mutation.
            mutation.dateFinished = now()
            mutation.rerun = False
            logger.debug("Saving mutation stats...")
            mutation.save()
            logger.debug("Done saving mutation stats...")

            # If all mutations in job are done, then set job as done.
            logger.debug("checkForCompletion")
            logger.debug("mutation jobs: {}".format(mutation.jobs.all()))

            logFile.flush()
            shutil.copy(logFile.name, os.path.join(settings.ELASPIC_LOG_PATH, logName + '.log'))

            checkForCompletion(mutation.jobs.all())

        # Remove logger.
        logger.debug("Removing logs. Say goodbye...")
        logger.handlers = []
        logFile.close()

        # Set current working directory and environment back to default.
        os.chdir(os.path.join(settings.PROJECT_ROOT, '..'))
        #~ os.environ = old_env

        # Delete temp folders.
        try:
            shutil.rmtree(os.environ['MPLCONFIGDIR'])
            os.environ['MPLCONFIGDIR'] = ''
        except Exception:
            pass

        # Return.
        # 0: Complete without errors.
        # 1: Complete with errors.
        # 2: Pipeline crash (log saved).
        # 3: Out of time, set in settings.py.
        # 4: Unknown error, not logged.
        # 5: Blacklisted protein.
        return exitCode if exitCode == -1 else 4
