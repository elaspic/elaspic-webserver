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


def _run_pipeline_remotely(mutation_dict, logger):
    js = JobSubmitter(logger=logger)

    for uniprot_id, mutations in mutation_dict.items():
        logger.debug("uniprot_id: {}, mutations: {}".format(uniprot_id, mutations))
        js.submitjob(uniprot_id, mutations)

    time.sleep(5)
    mutation_dict_output = {
        uniprot_id: {'mutations': mutations} 
        for (uniprot_id, mutations) 
        in mutation_dict.items()
    }
    while not all([('status' in v and v['status'] == "Done") for v in mutation_dict_output.values()]):
        logger.debug('mutation_dict_output: {}'.format(mutation_dict_output))
        for uniprot_id, mutations in mutation_dict.items():
            progress_dict = js.check_progress(uniprot_id, mutations)
            if progress_dict:
                for key, value in progress_dict.items():
                    if value:
                        mutation_dict_output[uniprot_id][key] = value
            else:
                mutation_dict_output[uniprot_id]['done'] = True
        time.sleep(60)
    return mutation_dict_output
    

@app.task(rate_limit='10/m', max_retries=2)
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
        _run_pipeline_remotely([(mutation.protein, mutation.mut,)], logger)
        
        # Save logs if we're debugging        
        if settings.DEBUG:
            logFile.flush()
            shutil.copy(logFile.name, os.path.join(settings.ELASPIC_LOG_PATH, logName + '.log'))

    except SoftTimeLimitExceeded:
        # Out of time. Cleanup!
        mutation.status = 'error'
        mutation.affectedType = ''
        mutation.error = '3: OUTATIME'
        exitCode = 3
        
    except Exception as e:
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
#                domains = Domain.objects.using('data').filter(protein_id=mutation.protein)
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
        
        # Remove logger.
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

    
        

@app.task(rate_limit='10/m', max_retries=2)
def runPipelineWrapperAll(mutations, jid):
    """
    If there are multiple mutations in the same protein, submit them together.
    """
    if not isinstance(mutations, list):
        mutations = [mutations]
        
    # Group mutations
    mutation_dict = dict()
    for mutation in mutations:
        mutation_dict.setdefault(mutation.protein, set()).add(mutation.mut)
    for key in mutation_dict:
        mutation_dict[key] = ','.join(mutation_dict[key])
        
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
    logger.info("mutation_dict: {}".format(mutation_dict))


    try:
        
        ### Run pipeline ###
        #_run_pipeline_locally(mutation, logger)
        mutation_dict_output = _run_pipeline_remotely(mutation_dict, logger)

        for mutation in mutations:
            mutation.provean_job_id = mutation_dict_output[mutation.protein].get('provean_job_id', None)
            mutation.model_job_id = mutation_dict_output[mutation.protein].get('model_job_id', None)
            mutation.mutation_job_id = mutation_dict_output[mutation.protein].get('mutation_job_id', None)
           
        
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
    
    
    finally:
        for mutation in mutations:
            # Fail-safe in case of sys.exit() or some other dangerous stuff is
            # called within the pipeline.
            if exitCode == -1:
                mutation.status = 'error'
                mutation.error = '2: PIPELINECRASH: EXIT STATUS 4'
            
            # Save mutation.
            mutation.dateFinished = now()
            mutation.rerun = False
            mutation.save()
        
            # If all mutations in job are done, then set job as done.
            checkForCompletion(mutation.jobs.all())

        # Remove logger.
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
