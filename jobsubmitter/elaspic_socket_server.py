# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 15:42:47 2015

@author: strokach
"""
import os
import os.path as op
import socketserver
import json
import re
import subprocess
import shlex
import time
import shutil
import logging

import pandas as pd



#%%
TESTING = False

# Delay between how often you check the filesystem for a file
DELAY_LOCK_EXISTS = int(os.environ.get('DELAY_LOCK_EXISTS') or os.environ.get('DELAY') or 30)
# Delay between how often you query qstat with a JOBID
DELAY_JOB_RUNNING = int(os.environ.get('DELAY_JOB_RUNNING') or os.environ.get('DELAY') or 30)

print('#' * 80)
print('DELAY_LOCK_EXISTS: {}'.format(DELAY_LOCK_EXISTS))
print('DELAY_JOB_RUNNING: {}'.format(DELAY_LOCK_EXISTS))



#%%
BASE_DIR = op.abspath(op.dirname(__file__))

from elaspic import conf
conf.read_configuration_file(op.join(BASE_DIR, 'config_file_mysql.ini'))
from elaspic import sql_db

LOG_DIR = op.join(BASE_DIR, 'log', 'socketserver')
PROVEAN_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'provean_locks')
MODEL_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'model_locks')
MUTATION_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'mutation_locks')

os.makedirs(op.join(LOG_DIR), exist_ok=True)
os.makedirs(op.join(PROVEAN_LOCK_DIR, 'finished'), exist_ok=True)
os.makedirs(op.join(MODEL_LOCK_DIR, 'finished'), exist_ok=True)
os.makedirs(op.join(MUTATION_LOCK_DIR, 'finished'), exist_ok=True)



#%%

class FileHandler(logging.FileHandler):    
    def _open(self):
        prevumask=os.umask(0o002)
        rtv=logging.FileHandler._open(self)
        os.umask(prevumask)
        return rtv


def _get_logger_name(uniprot_id=None, mutations=None, job_id=None):
    if uniprot_id is None and job_id is None:
        raise Exception
    if uniprot_id is not None:
        logger_name = '{}.{}'.format(uniprot_id, mutations)
    elif job_id is not None:
        logger_name = '{}'.format(job_id)
    else:
        raise Exception
    return logger_name


def _get_logger_filename(logger_name):
    return op.join(LOG_DIR, logger_name + '.log')


def get_logger(uniprot_id=None, mutations=None, job_id=None):
    """
    """
    if uniprot_id is None and job_id is None:
        raise Exception
    os.makedirs(LOG_DIR, exist_ok=True)
    logger_name = _get_logger_name(uniprot_id, mutations, job_id)
    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    fh = FileHandler(_get_logger_filename(logger_name))
    fh.setFormatter(formatter)
    logger.handlers = [sh, fh] 
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
#    debug_info = (
#        'uniprot_id: {}\t' 'mutations: {}\t' 'job_id: {}'
#        .format(uniprot_id, mutations, job_id)
#    )
#    logger.debug(debug_info)
    return logger



#%% 
class BadMessageException(Exception):
    pass


class BadJobIDException(Exception):
    pass


def _validate_message_dict(message_dict):
    if 'request' not in message_dict:
        raise BadMessageException("'request' not in `message_dict`!")
    for key in message_dict:
        if ' ' in message_dict[key]:
            raise BadMessageException("{}: {}".format(key, message_dict[key]))
    if 'job_id' in message_dict:
        if type(message_dict['job_id']) != int:
            raise BadMessageException("job_id: {}".format(message_dict['job_id']))



#%% Socket Server
class MyHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        message = self.request.recv(1024) # Max number of bytes read is 1024
        message_dict = json.loads(message.decode())
        
        _validate_message_dict(message_dict)
        if message_dict['request'] == 'submitjob':
            print("Submitting job for request: {}".format(message_dict))
            self._send_response({'status': 'Submitting job...'})
            ep = ElaspicPipeline(message_dict['uniprot_id'], message_dict['mutations'])
            ep.jobsubmitter()
            ep.close()
        elif message_dict['request'] == 'check_progress':
            print("Checking progress for request: {}".format(message_dict))
            ep = ElaspicPipeline(message_dict['uniprot_id'], message_dict['mutations'])
            ep.check_progress()
            self._send_response(ep.output_dict)
            ep.close()
        elif message_dict['request'] == 'jobstatus':
            print("Checking status for request: {}".format(message_dict))
            output_dict = jobstatus(message_dict['job_id'])
            self._send_response(output_dict)
        elif message_dict['request'] == 'jobstatus_full':
            print("Checking status for request: {}".format(message_dict))
            output_dict = jobstatus(message_dict['job_id'], full=True)
            self._send_response(output_dict)
        else:
            self._send_response({'status': 'Unrecognized request'})

    def _send_response(self, output_dict):
        ouput = json.dumps(output_dict).encode('utf-8')
        self.request.send(ouput)

class MyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True



#%%
class ElaspicPipeline(object):

    def __init__(self, uniprot_id, mutations):
        self.uniprot_id = uniprot_id
        self.mutations = mutations
        self.logger = get_logger(uniprot_id, mutations)
        self.output_dict = dict()
   
   
    def close(self):
        for handler in self.logger.handlers:
            handler.flush()
            handler.close()
   
   
    #==============================================================================
    # Helper functions
    #==============================================================================
       
    def lock_filename(self, run_type, finished=False):
        if run_type in ('p', 'provean'):
            lock_file = op.join(
                PROVEAN_LOCK_DIR, 
                'finished' if finished else '',
                '{}.lock'.format(self.uniprot_id))
        elif run_type in ('m', 'model'):
            lock_file = op.join(
                MODEL_LOCK_DIR, 
                'finished' if finished else '',
                '{}.lock'.format(self.uniprot_id))
        elif run_type in ('mut', 'mutations'):
            lock_file = op.join(
                MUTATION_LOCK_DIR, 
                'finished' if finished else '',
                '{}.{}.lock'.format(self.uniprot_id, self.mutations))
        else:
            raise Exception
        return lock_file

   
   
    #==============================================================================
    # Job Submitter     
    #==============================================================================
       
    def jobsubmitter(self):
        """
        This assumes that if we can't calculate a model, 
        we leave a note in the 'model_error' column.
        """
        self.logger.info('-' * 20 + ' jobsubmitter ' + '-' * 20)
        ## Provean and model
        # (want to submit both together so that they finish faster)
        run_types = {'provean': {}, 'model': {}}
        run_types['provean']['is_missing'], run_types['model']['is_missing'], have_domains = (
            self.check_precalculated()
        )

        # If we don't have any domains with structural template, don't go any further.
        if not have_domains:
            self.logger.info(
                "Uniprot {} does not have any domains with structural templates!"
                .format(self.uniprot_id)
            )
            with open(self.lock_filename('mut', True), 'w') as ofh:
                ofh.write('0') # 0 means no job_id
            self.output_dict.update({'status': "Done"})
        
        # If everything gets submitted, we avoid the loop below; no need to sleep.
        self.submitjob_with_lock(run_types) 
        while self._precalculated_data_missing(run_types):
            # Wait for lock-setters to finish and jobs to become un-missing...
            self.logger.debug('Sleeping for {} seconds.'.format(DELAY_LOCK_EXISTS))
            time.sleep(DELAY_LOCK_EXISTS)
            run_types['provean']['is_missing'], run_types['model']['is_missing'], have_domains = (
                self.check_precalculated()
            )
            self.submitjob_with_lock(run_types)
        self.release_lock(run_types)
        self.output_dict.update(run_types)
        
        ## Mutations
        run_types = {'mutations': {}}
        self.submitjob_with_lock(run_types)
        # If everything gets submitted, we avoid the loop below; no need to sleep
        while not all([v for v in run_types.values()]):
            self.logger.debug('Sleeping for {} seconds.'.format(DELAY_LOCK_EXISTS))
            time.sleep(DELAY_LOCK_EXISTS)
            self.submitjob_with_lock(run_types)
        self.release_lock(run_types)
        self.output_dict.update(run_types)
    
    
    def _precalculated_data_missing(self, run_types):
        is_missing = (
            (run_types['provean']['is_missing'] and run_types['provean'].get('lock_file') is None) or
            (run_types['model']['is_missing'] and run_types['model'].get('lock_file') is None)
        )
        return is_missing
    

    def submitjob_with_lock(self, run_types):
        self.logger.debug(
            "Trying to submit jobs for run_types: '{}'"
            .format(', '.join(run_types.keys()))
        )
        for run_type, data in run_types.items():
            self.logger.debug('runtype: {}'.format(run_type))
            if (data.get('is_missing') == False) or (data.get('lock_file')):
                self.logger.debug('Already calculated. Skipping.')
                continue
            self.logger.debug("Submitting run_type '{}'...".format(run_type))
            lock_file = self.lock_filename(run_type)
            try:
                lock = open(lock_file, 'x') # create lock
            except FileExistsError:
                self.logger.debug('Lockfile {} exists!'.format(lock_file))
                continue
            submitjob_output = self.qsub(run_type)
            self.logger.debug('submitjob_output: {}'.format(submitjob_output))
            job_id = submitjob_output['job_id']
            lock.write(str(job_id))
            run_types[run_type].update({'lock_file': lock_file, 'job_id': job_id})
    
    
    def release_lock(self, run_types):
        self.logger.debug(
            "Trying to release locks on run_types: '{}'."
            .format(', '.join(run_types.keys()))
        )
        for run_type, data in run_types.items():
            self.logger.debug('runtype: {}'.format(run_type))
            if 'lock_file' not in data:
                self.logger.debug('No lockfile written. Skipping.')
                continue            
            jobstatus_output = jobstatus(data['job_id'])
            while jobstatus_output['status'] != "Done":
                self.logger.debug('jobstatus_output: {}'.format(jobstatus_output))
                self.logger.debug('sleeping...')
                time.sleep(DELAY_JOB_RUNNING)
                jobstatus_output = jobstatus(data['job_id'])
            shutil.move(
                data['lock_file'], 
                op.join(op.dirname(data['lock_file']), 'finished', op.basename(data['lock_file'])))
            run_types[run_type].update(jobstatus_output)
        self.logger.debug('release_lock: {}'.format(run_types))
        
    
    def qsub(self, run_type):
        # Submit job
        if TESTING:
            job_id = 99999
        else:
            system_command = (
                'qsub -v uniprot_id="{}" -v mutations="{}" submitjob_{}.sh'
                .format(self.uniprot_id, self.mutations, run_type)
            )
            output = self._run_system_command(system_command)
            job_id = self._extract_job_id(output)
        
        # Prepare output
        output_dict = {'job_id': job_id, "status": "Queued"}
        return output_dict
        
    
    def _run_system_command(self, system_command, n_tries_max=5):
        args = shlex.split(system_command)
        n_tries = 0
        while True:
            try:
                output = subprocess.check_output(args, timeout=10)
                break
            except subprocess.CalledProcessError as e:
                if n_tries < n_tries_max:
                    n_tries += 1
                    continue
                else:
                    raise e
        return output.decode()
    
    
    def _extract_job_id(self, output):
        """
        e.g.
        'Your job 3259443 ("elaspic") has been submitted' -> 3259443
        """
        job_ids = re.findall('Your job (\d*) .*', output)
        if len(job_ids) != 1 or not job_ids[0].isdigit():
            error_message = (
                'output: {}\n'.format(output),
                'job_ids: {}'.format(job_ids),        
            )
            raise BadJobIDException(error_message)
        return int(job_ids[0])
    
    

    #==============================================================================
    # Precalculated data checker
    #==============================================================================

    select_provean_query = """
select 
uniprot_id
from {db_schema}.provean
where uniprot_id = '{uniprot_id}'
and provean_supset_filename is not null
"""

    select_domain_model_query = """
select
uniprot_domain_id, model_filename, model_errors
from {db_schema}.uniprot_domain
join {db_schema}.uniprot_domain_template using (uniprot_domain_id)
left join {db_schema}.uniprot_domain_model using (uniprot_domain_id)
where uniprot_id = '{uniprot_id}'
"""

    select_domain_pair_model_query = """
select
uniprot_domain_pair_id, model_filename, model_errors
from {db_schema}.uniprot_domain_pair
join {db_schema}.uniprot_domain_pair_template using (uniprot_domain_pair_id)
left join {db_schema}.uniprot_domain_pair_model using (uniprot_domain_pair_id)
where uniprot_domain_id_1 in ({uniprot_domain_ids})
or uniprot_domain_id_2 in ({uniprot_domain_ids})
"""
    
    def check_precalculated(self):
        db = sql_db.MyDatabase(conf.configs, self.logger)
        
        configs_copy = conf.configs.copy()
        configs_copy['uniprot_id'] = self.uniprot_id
        provean = (
            pd.read_sql_query(self.select_provean_query.format(**configs_copy), db.engine)
        )
        domain_model = (
            pd.read_sql_query(self.select_domain_model_query.format(**configs_copy), db.engine)
        )
        provean_is_missing = (len(provean) == 0) & (len(domain_model) > 0)
        model_is_missing = (
            (len(domain_model[
                domain_model['model_filename'].isnull() &
                domain_model['model_errors'].isnull()]) > 0)
        )
        have_domains = len(domain_model)
        
        # Do this only if we have at least one domain
        if len(domain_model) and not model_is_missing:
            configs_copy['uniprot_domain_ids'] = (
                ', '.join(domain_model['uniprot_domain_id'].drop_duplicates().astype(str))
            )
            domain_pair_model = (
                pd.read_sql_query(self.select_domain_pair_model_query.format(**configs_copy), db.engine)
            )
            model_is_missing = (
                model_is_missing |
                (len(domain_pair_model[
                    domain_pair_model['model_filename'].isnull() &
                    domain_pair_model['model_errors'].isnull()]) > 0)
            )
        
        info_message = (
            'provean_is_missing: {}\t'.format(provean_is_missing) + 
            ' model_is_missing: {}\t'.format(model_is_missing) +
            ' have_domains: {}'.format(have_domains)
        )
        self.logger.info(info_message)
        return provean_is_missing, model_is_missing, have_domains
    
    
    
    #==============================================================================
    # Progress checker    
    #==============================================================================
    
    def check_progress(self):
        self.logger.info('-' * 20 + ' check_progress ' + '-' * 20)
        for contents in self._read_file(self.lock_filename('provean')):
            self.output_dict['provean_job_id'] = contents
        for contents in self._read_file(self.lock_filename('model')):
            self.output_dict['model_job_id'] = contents
        for contents in self._read_file(self.lock_filename('mutations')):
            self.output_dict['mutation_job_id'] = contents
        for contents in self._read_file(self.lock_filename('mutations', finished=True)):
            self.output_dict['status'] = "Done"
    
    
    def _read_file(self, filename):
        """Yield file contents if the file exists.
        """
        try:
            with open(filename, 'r') as ifh:
                yield ifh.read()
        except FileNotFoundError:
            pass
    



#%%
def jobstatus(job_id, full=False):
    """Check job status.
    
    Look for job with the 'job_id' as specified in the `message_dict`.
    
    Returns
    -------
    output_dict : dict
        Contains info about the specified job.
        
    output_dict['status'] : str
        "Running" if job is running. "Done" if job is not running.
        
    output_dict['qstat_log'] : str
        Output of the ``qstat`` command for a running job.
        
    output_dict['stdout_log'] : str
        Job's STDOUT.
        
    output_dict['stderr_log'] : str
        Job's STDERR.
    """
    output_dict = {'job_id': job_id}

    if TESTING:
        output, error_message = '', 'Following jobs do not exist'
    else:
        system_command = 'qstat -j {}'.format(job_id)
        args = shlex.split(system_command)
        child_process = (
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        )
        output, error_message = map(bytes.decode, child_process.communicate())
    
    if not error_message:
        output_dict['status'] = "Running"
    elif 'Following jobs do not exist' in error_message:
        output_dict['status'] = "Done"
    else:
        error_message = (
            'output: {}\n'.format(output),
            'error_message: {}\n'.format(error_message),
        )
        raise Exception(error_message)

    if full:
        if TESTING:
            raise Exception('Full output is not supported in TESTING mode.')
        if output_dict['status'] == "Running":
            output_dict['qstat_log'] = output
        # Locate the pbs-output dir with job logs
        pbs_output_path = op.join(op.dirname(__file__), 'pbs-output')
        pbs_stdout_name = op.join(pbs_output_path, '{}.out'.format(job_id))
        pbs_stderr_name = op.join(pbs_output_path, '{}.err'.format(job_id))
        with open(pbs_stdout_name, 'r') as ifh:
            output_dict['stdout_log'] = ifh.read()
        with open(pbs_stderr_name, 'r') as ifh:
            output_dict['stderr_log'] = ifh.read()
    
    return output_dict



#%% Main
if __name__ == '__main__':
    address = ('192.168.6.201', 59462) # let the kernel give us a port
    server = MyServer(address, MyHandler)
    ip, port = server.server_address # find out what port we were given
    print(ip, port)
    
    server.serve_forever()
    
