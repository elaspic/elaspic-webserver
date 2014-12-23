import os
from shutil import rmtree
from socket import gethostname
from time import time, sleep
from datetime import timedelta

from django.utils.timezone import now, localtime
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q

from celery.task.control import inspect
from celery.result import AsyncResult

from web_pipeline.models import Job, Mut
from web_pipeline.functions import checkForCompletion


class CleanupManager(object):
    
    def __init__(self, dosleep=True):
        # Sleep to allow pipeline to finish up.
        if dosleep:
            sleep(5)
            
    def checkForStalledMuts(self, job=None):
        if job:
            js = Job.objects.filter(jobID=job)
        else:
            js = Job.objects.filter(isDone=False)
        
        for j in js:
            muts = j.muts.filter(Q(status='queued') | Q(status='running') | Q(rerun=1) | Q(rerun=2))
            for mut in muts:
                if AsyncResult(mut.taskId).failed():
                    mut.status = 'error'
                    mut.affectedType = None
                    mut.error = '2: PIPELINECRASH: DB ERROR'
                    mut.dateFinished = now()
                    mut.rerun = False
                    mut.save()

        checkForCompletion(js)
        

    
    def removeOldJobs(self):
        """ Fetch and delete all jobs last visited too long ago. """
        js = Job.objects.filter(dateVisited__lte=now()-timedelta(days=settings.JOB_EXPIRY_DAY ))
        for j in js:
            # Delete link to all mutations.
            j.jobtomut_set.all().delete()
            j.delete()
            
        # Delete all local files without a job.
        for dirs in os.listdir(settings.SAVE_PATH):
            j = Job.objects.filter(jobID=dirs)
            if not j:
                try:
                    rmtree(os.path.join(settings.SAVE_PATH, dirs))
                except Exception:
                    pass
        
        # Delete old temp files.
        for somefolder in [d for d in os.listdir('/tmp/') if d[:8] == 'elaspic_']:
            mtime = os.path.getmtime(os.path.join('/tmp', somefolder))
            if mtime < time() - settings.CELERYD_TASK_TIME_LIMIT:
                try:
                    rmtree(os.path.join('/tmp', somefolder))
                except Exception:
                    pass
    
    
    def checkForStalledJobs(self):
        """ Checks that all running and queued mutations actually are doing so. 
            THIS DOES NOT WORK PROPERLY. SEVERAL JOBS ARE STARTED THAT ARE NOT
            NEEDED. DO NOT CALL THIS METHOD. """
    
        # Set hostname and celery inspect object.
        pc = 'w1@elaspic' if settings.COMPUTERNAME == 'elaspic' else 'celery@' + gethostname() 
        i = inspect()
        lostMutations, toRunAgain  = [], []
    
        # Check that queued jobs are in Celery.
        queuedMutsDB = Mut.objects.filter(Q(status='queued') | Q(rerun=1))
        queuedMutsCel = [t['args'].split('<Mut: ')[1].split('>, ')[0] if '<Mut:' in t['args'] else 'cleanup' for t in i.reserved()[pc]]
        for mdb in queuedMutsDB:
            mdbstring = "%s.%s" % (mdb.protein, mdb.mut)
            if not mdbstring in queuedMutsCel:
                lostMutations.append(mdb)

        # Check that all runnings jobs are in celery active list.
        activeMutsDB = Mut.objects.filter(Q(status='running') | Q(rerun=2))
        activeMutsCel = [t['args'].split('<Mut: ')[1].split('>, ')[0] if '<Mut:' in t['args'] else 'cleanup' for t in i.active()[pc]]
        for mdb in activeMutsDB:
            mdbstring = "%s.%s" % (mdb.protein, mdb.mut)
            if not mdbstring in activeMutsCel:
                mdb.rerun = 1 if mdb.rerun == 2 else mdb.rerun
                mdb.status = 'queued' if mdb.status == 'running' else mdb.status
                mdb.save()
                lostMutations.append(mdb)
                
        # Return lost mutations.
        for m in lostMutations:
            try:
                job = m.jobs.all()[0]
            except Exception:
                m.delete()
                continue
            toRunAgain.append([m, job.jobID])
            
        return toRunAgain
                
    
    
    def sendCrashLogs(self):
        
        # Get all crash logs.
        crashLogs = os.listdir(settings.CRASH_LOG_PATH)
    
        if crashLogs:
            
            # Send crash logs to all admins.
            if settings.SEND_CRASH_LOGS_TO_ADMINS:
            
                topic = 'ELASPIC: %d crash logs for %s' % (len(crashLogs), 
                                                           localtime(now()).date())
                message = EmailMessage(topic, 'Crash logs attached.',
                                       'ELASPIC@ELASPIC.com',
                                       [a[1] for a in settings.ADMINS])      
                for log in crashLogs:
                    message.attach_file(os.path.join(settings.CRASH_LOG_PATH, log),
                                        'text/plain')
                try:
                    message.send()
                except Exception:
                    pass
                else:
                    for log in crashLogs:
                        os.remove(os.path.join(settings.CRASH_LOG_PATH, log))
            
            # Save crash logs for 90 days if not send by email.
            else:
                for log in crashLogs:
                    logPath = os.path.join(settings.CRASH_LOG_PATH, log)
                    if os.path.getmtime(logPath) < time() - timedelta(days=90).total_seconds():
                        try: 
                            os.remove(logPath)
                        except Exception:
                            pass