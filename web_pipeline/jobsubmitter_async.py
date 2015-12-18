# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 23:40:40 2015

@author: strokach
"""
import os
import time
import shutil
import shlex
import re
import subprocess
import logging
import tempfile
import asyncio

import os.path as op
import numpy as np
import pandas as pd

from elaspic import conf

configs = conf.Configs()
logger = logging.getLogger()



def main(args):







# %%
TESTING = False

# Delay between how often you check the filesystem for a file
DELAY_LOCK_EXISTS = int(os.environ.get('DELAY_LOCK_EXISTS') or os.environ.get('DELAY') or 30)
# Delay between how often you query qstat with a JOBID
DELAY_JOB_RUNNING = int(os.environ.get('DELAY_JOB_RUNNING') or os.environ.get('DELAY') or 30)

BASE_DIR = op.abspath(op.dirname(__file__))
USER_INPUT_DIR = '/home/kimlab1/database_data/elaspic_v2/user_input'

conf.read_configuration_file(op.join(USER_INPUT_DIR, 'config_file_mysql.ini'))

LOG_DIR = op.join('/tmp', 'jobsubmitter', 'log')
PROVEAN_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'provean_locks')
MODEL_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'model_locks')
MUTATION_LOCK_DIR = op.join('/tmp', 'jobsubmitter', 'mutation_locks')

logger.info('#' * 80)
logger.info('DELAY_LOCK_EXISTS: {}'.format(DELAY_LOCK_EXISTS))
logger.info('DELAY_JOB_RUNNING: {}'.format(DELAY_LOCK_EXISTS))

os.makedirs(op.join(LOG_DIR), exist_ok=True)
os.makedirs(op.join(PROVEAN_LOCK_DIR, 'finished'), exist_ok=True)
os.makedirs(op.join(MODEL_LOCK_DIR, 'finished'), exist_ok=True)
os.makedirs(op.join(MUTATION_LOCK_DIR, 'finished'), exist_ok=True)


# %% Logger
class FileHandler(logging.FileHandler):
    def _open(self):
        prevumask = os.umask(0o002)
        rtv = logging.FileHandler._open(self)
        os.umask(prevumask)
        return rtv


def _get_logger_name(protein_id=None, mutations=None, job_id=None):
    if protein_id is None and job_id is None:
        raise Exception
    if protein_id is not None:
        logger_name = '{}.{}'.format(protein_id, mutations)
    elif job_id is not None:
        logger_name = '{}'.format(job_id)
    else:
        raise Exception
    return logger_name[:255]


def _get_logger_filename(logger_name):
    return op.join(LOG_DIR, logger_name + '.log')


def configure_logger(logger, protein_id=None, mutations=None, job_id=None):
    """
    """
    if protein_id is None and job_id is None:
        raise Exception()
    os.makedirs(LOG_DIR, exist_ok=True)
    logger_name = _get_logger_name(protein_id, mutations, job_id)
    # logger = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    fh = FileHandler(_get_logger_filename(logger_name))
    fh.setFormatter(formatter)
    logger.handlers = [sh, fh]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


# %% Errors
class BadMessageException(Exception):
    pass


class BadJobIDException(Exception):
    pass


# %% Main
# @app.task(rate_limit='10/m', max_retries=2)
def main(args):

    if 'fields' in args:
        fields = [field for field in args['fields'].split(',') if field]
        include_pbs_output = 'stdout_log' in fields or 'stderr_log' in fields
    else:
        fields = []
        include_pbs_output = False
    validate_args(args)

    # Submit jobs
    if args['uniprot_id']:
        # uniprot ID / mutation from the database
        js = DatabaseJobSubmitter(
            args['uniprot_id'], args['mutations'])

    elif args['unique_id']:
        # structure (+ sequence) saved to the unique folder
        js = LocalJobSubmitter(
            args['unique_id'], args['pdb_filename'], args['sequence_filename'], args['mutations'])

    elif args['pdb_file']:
        # pdb file (+ sequence file) given as raw input
        logger.debug('pdb_file: {}'.format(args['pdb_file']))
        logger.debug('sequence_file: {}'.format(args['sequence_file']))

        unique_temp_dir = tempfile.mkdtemp(prefix='', dir=USER_INPUT_DIR)
        unique_id = op.basename(unique_temp_dir)

        pdb_filename = args['pdb_file'].filename
        logger.debug('pdb_filename: {}'.format(pdb_filename))
        args['pdb_file'].save(op.join(unique_temp_dir, pdb_filename))

        sequence_filename = None
        if args['sequence_file']:
            sequence_filename = args['sequence_file'].filename
            logger.debug('sequence_filename: {}'.format(sequence_filename))
            args['sequence_file'].save(op.join(unique_temp_dir, sequence_filename))

        js = LocalJobSubmitter(
            unique_id, pdb_filename, sequence_filename, args['mutations'])

    else:
        raise RuntimeError

    js.submit_job()
    logger.debug('Submitted job.')

    output = js.check_progress(include_pbs_output)
    logger.debug('Read job output.')

    # Filter output
    def _filter_dict_recursively(input_dict):
        if not isinstance(input_dict, dict):
            return input_dict
        output_dict = dict()
        for key in input_dict:
            if key not in fields and key not in args['mutations']:
                continue
            value = input_dict[key]
            if isinstance(value, dict):
                value = _filter_dict_recursively(value)
            if isinstance(value, list):
                value = [_filter_dict_recursively(d) for d in value]
            output_dict[key] = value
        return output_dict

    logger.debug(
        "Filtering output to include only the fields specified "
        "by the 'fields' argument."
    )
    output_filtered = _filter_dict_recursively(output)
    return output_filtered


def validate_args(self, args):
    if not args['uniprot_id'] and not args['unique_id'] and not args['pdb_file']:
        message = (
            "Either 'uniprot_id', 'unique_id', or 'pdb_data' must be specified!"
        )
        logger.error(message)
        raise ValueError


# %%
class JobSubmitter:

    def __init__(self, protein_id, mutations):
        self.protein_id = protein_id
        self.mutations = [mut for mut in mutations.split(',') if mut]
        logger.debug('self.mutations: {}'.format(self.mutations))

        # To be set by child classes
        self.pdb_file = ''
        self.sequence_file = ''
        self.uniprot_domain_pair_ids = ''

    # Pipeline for building sequences, models, and mutations
    def submit_job(self):
        """
        This assumes that if we can't calculate a model,
        we leave a note in the 'model_error' column.
        """
        logger.info('-' * 20 + ' submit_job ' + '-' * 20)

        # Provean and Model (want to submit both together so that they finish faster)
        run_types = {'sequence': {}, 'model': {}}
        run_types['sequence']['is_missing'], run_types['model']['is_missing'], have_domains = (
            self.check_precalculated()
        )
        logger.debug('run_types: {}'.format(run_types))

        # If we don't have any domains with structural template, don't go any further.
        if not have_domains:
            logger.info(
                "Uniprot {} does not have any domains with structural templates!"
                .format(self.protein_id)
            )
            with open(self.get_lock_file('mut', True), 'w') as ofh:
                ofh.write('0')  # 0 means no job_id

        # If everything gets submitted, we avoid the loop below; no need to sleep.
        logger.debug('Submit job with lock...')
        self.submitjob_with_lock(run_types)
        while self._precalculated_data_missing(run_types):
            # Wait for lock-setters to finish and jobs to become un-missing...
            logger.debug('Sleeping for {} seconds.'.format(DELAY_LOCK_EXISTS))
            time.sleep(DELAY_LOCK_EXISTS)
            run_types['sequence']['is_missing'], run_types['model']['is_missing'], have_domains = (
                self.check_precalculated()
            )
            self.submitjob_with_lock(run_types)
        self.release_lock(run_types)
        logger.debug('run_types: {}'.format(run_types))

        # Mutations
        logger.debug('Submit job with lock for mutations...')
        run_types = {mut: {} for mut in self.mutations}
        self.submitjob_with_lock(run_types)
        # If everything gets submitted, we avoid the loop below; no need to sleep
        while not all([v for v in run_types.values()]):
            logger.debug('Sleeping for {} seconds.'.format(DELAY_LOCK_EXISTS))
            time.sleep(DELAY_LOCK_EXISTS)
            self.submitjob_with_lock(run_types)
        self.release_lock(run_types)

    def _precalculated_data_missing(self, run_types):
        is_missing = (
            (run_types['sequence']['is_missing'] and
             run_types['sequence'].get('lock_file') is None) or
            (run_types['model']['is_missing'] and
             run_types['model'].get('lock_file') is None)
        )
        return is_missing

    # %% These functions work on a `run_types` dictionary.
    def submitjob_with_lock(self, run_types):
        """
        Parameters
        ----------
        run_types : dictionary of different run types (e.g. 'sequence', 'model', ... )
        """
        logger.debug(
            "Trying to submit jobs for run_types: '{}'"
            .format(', '.join(run_types.keys()))
        )
        for key, value in run_types.items():
            logger.debug('run_type: {}'.format(key))
            if (value.get('is_missing') == False) or (value.get('lock_file')):
                logger.debug('Already calculated. Skipping.')
                continue
            logger.debug("Submitting run_type '{}'...".format(key))
            lock_file = self.get_lock_file(key)
            try:
                lock = open(lock_file, 'x')  # create lock
            except FileExistsError:
                logger.debug('Lockfile {} exists!'.format(lock_file))
                continue
            lock_file_finished = self.get_lock_file(key, finished=True)
            try:
                os.remove(lock_file_finished)
                logger.debug(
                    'Removed lockfile {} from a previous job.'
                    .format(lock_file_finished))
            except FileNotFoundError:
                pass
            submitjob_output = self.qsub(key)
            logger.debug('submitjob_output: {}'.format(submitjob_output))
            job_id = submitjob_output['job_id']
            lock.write(str(job_id))
            run_types[key].update({'lock_file': lock_file, 'job_id': job_id})

    def release_lock(self, run_types):
        logger.debug(
            "Trying to release locks on run_types: '{}'."
            .format(', '.join(run_types.keys()))
        )
        for run_type, data in run_types.items():
            logger.debug('runtype: {}'.format(run_type))
            if 'lock_file' not in data:
                logger.debug('No lockfile written. Skipping.')
                continue
            jobstatus_output = jobstatus(data['job_id'])
            while jobstatus_output['status'] != "Done":
                logger.debug('jobstatus_output: {}'.format(jobstatus_output))
                logger.debug('sleeping...')
                time.sleep(DELAY_JOB_RUNNING)
                jobstatus_output = jobstatus(data['job_id'])
            shutil.move(
                data['lock_file'],
                op.join(op.dirname(data['lock_file']), 'finished', op.basename(data['lock_file'])))
            run_types[run_type].update(jobstatus_output)
        logger.debug('release_lock: {}'.format(run_types))

    # %% Submit job
    def qsub(self, run_type):
        if run_type.startswith('sequence'):
            run_type_idx = 1
            mutation = ''
        elif run_type.startswith('model'):
            run_type_idx = 2
            mutation = ''
        else:
            run_type_idx = 3
            mutation = run_type
        # Submit job
        if TESTING:
            job_id = 99999
        else:
            system_command = (
                'qsub -v uniprot_id="{protein_id}" -v unique_id="{protein_id}" '
                '-v pdb_file="{pdb_file}" -v sequence_file="{sequence_file}" '
                '-v mutations="{mutations}" '
                '-v uniprot_domain_pair_ids="{uniprot_domain_pair_ids}" '
                '{script_dir}/{prefix}_{run_type}.sh'
                .format(
                    protein_id=self.protein_id,
                    pdb_file=self.pdb_file,
                    sequence_file=self.sequence_file,
                    mutations=mutation,
                    uniprot_domain_pair_ids=self.uniprot_domain_pair_ids,
                    script_dir=op.join(BASE_DIR, 'scripts'),
                    prefix=self.SCRIPT_PREFIX,
                    run_type=run_type_idx)
            )
            logger.debug('qsub system command: {}'.format(system_command))
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

    # %% Helper functions
    def get_lock_file(self, run_type, finished=False):
        """
        """
        if run_type.startswith('sequence'):
            lock_files = op.join(
                PROVEAN_LOCK_DIR,
                'finished' if finished else '',
                '{}.lock'.format(self.protein_id))
        elif run_type.startswith('model'):
            lock_files = op.join(
                MODEL_LOCK_DIR,
                'finished' if finished else '',
                '{}.lock'.format(self.protein_id))
        else:
            mutation = run_type
            lock_files = op.join(
                MUTATION_LOCK_DIR,
                'finished' if finished else '',
                '{}.{}.lock'.format(self.protein_id, mutation))
        return lock_files

    # %% Progress checker
    def check_progress(self, include_pbs_output=False):
        """
        Parameters
        ----------
        pbs_output : bool
            If True, include stdout and stderr produced by the job(s).
        """
        logger.info('-' * 20 + ' check_progress ' + '-' * 20)

        run_types = ['sequence', 'model'] + self.mutations
        output_dict = {run_type: {} for run_type in run_types}
        output_dict['sequence']['is_missing'], output_dict['model']['is_missing'], __ = (
            self.check_precalculated()
        )

        for run_type in run_types:
            if op.isfile(self.get_lock_file(run_type)):
                with open(self.get_lock_file(run_type)) as ifh:
                    output_dict[run_type]['job_id'] = ifh.read()
                if include_pbs_output:
                    output_dict[run_type].update(
                        self._get_pbs_output(output_dict[run_type]['job_id']))
                output_dict[run_type]['status'] = 'Running'
            elif op.isfile(self.get_lock_file(run_type, finished=True)):
                with open(self.get_lock_file(run_type, finished=True)) as ifh:
                    output_dict[run_type]['job_id'] = ifh.read()
                if include_pbs_output:
                    output_dict[run_type].update(
                        self._get_pbs_output(output_dict[run_type]['job_id']))
                output_dict[run_type]['status'] = 'Done'
            else:
                output_dict[run_type]['status'] = 'Unknown'

        for mutation in self.mutations:
            if output_dict[mutation]['status'] != 'Running':
                output_dict[mutation]['result'] = self.get_final_results(mutation)

        return output_dict

    def _get_pbs_output(self, job_id):
        # Locate the pbs-output dir with job logs
        output_dict = dict()
        pbs_stdout_file = op.join(self.pbs_output_dir, '{}.out'.format(job_id))
        pbs_stderr_file = op.join(self.pbs_output_dir, '{}.err'.format(job_id))
        try:
            with open(pbs_stdout_file) as ifh:
                output_dict['stdout_log'] = ifh.read()
        except FileNotFoundError:
            output_dict['stdout_log'] = 'Error: File does not exist!'
        if op.isfile(pbs_stderr_file):
            with open(pbs_stderr_file) as ifh:
                output_dict['stderr_log'] = ifh.read()
        else:
            output_dict['stderr_log'] = 'Error: File does not exist!'
        return output_dict

#
#    @property
#    def result(self):
#        output_dict = self.check_progress()
#        logger.debug('output_dict: {}'.format(output_dict))
#        return output_dict


# %%
class DatabaseJobSubmitter(JobSubmitter):

    SCRIPT_PREFIX = 'database'

    def __init__(self, protein_id, mutations, uniprot_domain_pair_ids=''):
        super().__init__(protein_id, mutations)
        self.pbs_output_dir = op.join(BASE_DIR, 'pbs-output')

        from elaspic import database
        db = database.MyDatabase()
        self.db = db
        self.uniprot_domain_pair_ids = uniprot_domain_pair_ids

    # %% Look for precalculated data
    select_provean_query = """
select
uniprot_id
from {db_schema}.provean
where uniprot_id = '{protein_id}'
and provean_supset_filename is not null
"""

    select_domain_model_query = """
select
uniprot_domain_id, model_filename, model_errors
from {db_schema}.uniprot_domain
join {db_schema}.uniprot_domain_template using (uniprot_domain_id)
left join {db_schema}.uniprot_domain_model using (uniprot_domain_id)
where uniprot_id = '{protein_id}'
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
        logger.debug('Check precalculated...')

        configs_copy = configs.copy()
        configs_copy['protein_id'] = self.protein_id

        # Provean
        provean_query = self.select_provean_query.format(**configs_copy)
        # logger.debug('Provean SQL query:{}\n'.format(provean_query))
        provean = pd.read_sql_query(provean_query, self.db.engine)
        # logger.debug('provean: {}'.format(provean))

        # Domain Model
        domain_model_query = self.select_domain_model_query.format(**configs_copy)
        # logger.debug('Domain model SQL query:{}\n'.format(domain_model_query))
        domain_model = pd.read_sql_query(domain_model_query, self.db.engine)
        # logger.debug('domain_model: {}'.format(domain_model))

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
            domain_pair_model_query = self.select_domain_pair_model_query.format(**configs_copy)
            # logger.debug('Domain pair model SQL query:{}\n'.format(domain_pair_model_query))
            domain_pair_model = pd.read_sql_query(domain_pair_model_query, self.db.engine)
            # logger.debug('domain_pair_model: {}'.format(domain_pair_model))

            model_is_missing = (
                model_is_missing |
                (len(domain_pair_model[
                    domain_pair_model['model_filename'].isnull() &
                    domain_pair_model['model_errors'].isnull()]) > 0)
            )

        info_message = (
            'provean_is_missing: {}\t'.format(provean_is_missing) +
            'model_is_missing: {}\t'.format(model_is_missing) +
            'have_domains: {}'.format(have_domains)
        )
        logger.info(info_message)
        return provean_is_missing, model_is_missing, have_domains

    # %% Query the database for results
    sequence_query = """\
select *
from uniprot_kb.uniprot_sequence
where uniprot_id = '{0}'
"""

    domain_mutation_query = """
select *
from elaspic.uniprot_domain_mutation udmut
join elaspic.provean p using (uniprot_id)
join elaspic.uniprot_domain_model udm using (uniprot_domain_id)
join elaspic.uniprot_domain_template udt using (uniprot_domain_id)
join elaspic.uniprot_domain ud using (uniprot_domain_id, uniprot_id)
where udmut.uniprot_id = '{0}' and udmut.mutation = '{1}'
"""

    domain_pair_mutation_query = """
select *
from elaspic.uniprot_domain_pair_mutation udpmut
join elaspic.provean p using (uniprot_id)
join elaspic.uniprot_domain_pair_model udpm using (uniprot_domain_pair_id)
join elaspic.uniprot_domain_pair_template udpt using (uniprot_domain_pair_id)
join elaspic.uniprot_domain_pair udp using (uniprot_domain_pair_id)
where udpmut.uniprot_id = '{0}' and udpmut.mutation = '{1}'
"""

    def get_final_results(self, mutation):
        domain_mutation_df = pd.read_sql_query(
            self.domain_mutation_query.format(self.protein_id, mutation),
            self.db.engine)
        if domain_mutation_df.empty:
            logger.debug('No domain mutations found!!!')
            return dict()
        domain_pair_mutation_df = pd.read_sql_query(
            self.domain_pair_mutation_query.format(self.protein_id, mutation),
            self.db.engine)

        # Add sequence
        uniprot_sequence = pd.read_sql_query(
            self.sequence_query.format(self.protein_id), self.db.engine
        )
        if uniprot_sequence.empty:
            logger.debug('No uniprot sequence found!!!')
            return dict()
        else:
            logger.debug(uniprot_sequence)
            uniprot_sequence = uniprot_sequence.iloc[0]['uniprot_sequence']
        domain_mutation_df['sequence'] = uniprot_sequence
        domain_pair_mutation_df['sequence'] = uniprot_sequence

        # Datetime columns don't get serialized as json
        domain_mutation_df = self._convert_datetime_to_string(domain_mutation_df)
        domain_pair_mutation_df = self._convert_datetime_to_string(domain_pair_mutation_df)

        #
        self._format_domain_mutation_df(domain_mutation_df)
        self._format_domain_pair_mutation_df(domain_pair_mutation_df)

        #
        mutation_results = (
            domain_mutation_df.to_dict(orient='records') +
            domain_pair_mutation_df.to_dict(orient='records')
        )
        return mutation_results

    def _convert_datetime_to_string(self, df, fmt='%Y-%m-%d %H:%M:%S'):
        # TODO: There probably exists a more elegant way to find datetime columns
        datetime_columns = df.columns[
            (df.dtypes != int) &
            (df.dtypes != float) &
            (df.dtypes != object)
        ]
        for col in datetime_columns:
            df[col] = df[col].apply(lambda x: x.strftime(fmt))
        return df

    def _format_domain_mutation_df(self, df):
        if df.empty:
            return
        df['core_or_interface'] = 'core'
        df['provean_supset_file'] = df[['path_to_data', 'provean_supset_filename']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['provean_supset_file_2'] = df['provean_supset_file'].apply(
            lambda x: x + '.fasta')
        df['alignment_file'] = df[['path_to_data', 'alignment_filename']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file'] = df[['path_to_data', 'model_filename']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file_wt'] = df[['path_to_data', 'model_filename_wt']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file_mut'] = df[['path_to_data', 'model_filename_mut']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)

    def _format_domain_pair_mutation_df(self, df):
        if df.empty:
            return
        df['core_or_interface'] = 'interface'
        df['provean_supset_file'] = df[['path_to_data', 'provean_supset_filename']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['provean_supset_file_2'] = df['provean_supset_file'].apply(
            lambda x: x + '.fasta')
        df['alignment_file_1'] = df[['path_to_data', 'alignment_filename_1']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['alignment_file_2'] = df[['path_to_data', 'alignment_filename_2']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file'] = df[['path_to_data', 'model_filename']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file_wt'] = df[['path_to_data', 'model_filename_wt']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)
        df['model_file_mut'] = df[['path_to_data', 'model_filename_mut']].apply(
            lambda x: op.join(configs.archive_dir, x[0], x[1]), axis=1)


# %%
class LocalJobSubmitter(JobSubmitter):

    SCRIPT_PREFIX = 'local'

    def __init__(self, unique_id, pdb_file, sequence_file, mutations):
        super().__init__(unique_id, mutations)
        self.data_dir = op.join(USER_INPUT_DIR, self.protein_id)
        self.pbs_output_dir = op.join(self.data_dir, 'pbs-output')

        if pdb_file is None:
            self.pdb_file = ''
        elif op.isabs(pdb_file):
            self.pdb_file = pdb_file
        else:
            self.pdb_file = op.join(self.data_dir, pdb_file)

        if sequence_file is None:
            self.sequence_file = ''
        elif op.isabs(sequence_file):
            self.sequence_file = sequence_file
        else:
            self.sequence_file = op.join(self.sequence_file, sequence_file)

    def check_precalculated(self):
        logger.debug('Check precalculated...')
        #
        sequence_result_file = op.join(self.data_dir, 'sequence.json')
        if op.isfile(sequence_result_file):
            sequence_is_missing = False
        else:
            sequence_is_missing = True
        #
        model_result_file = op.join(self.data_dir, 'model.json')
        if op.isfile(model_result_file):
            model_is_missing = False
        else:
            model_is_missing = True
        #
        return sequence_is_missing, model_is_missing, True

    # %% Get results from flatfiles
    def get_final_results(self, mutation):
        mutation_result_file = op.join(self.data_dir, 'mutation_{}.json'.format(mutation))
        if op.isfile(mutation_result_file):
            mutation_result = pd.read_json(mutation_result_file)
        else:
            return []
        model_result = pd.read_json(op.join(self.data_dir, 'model.json'))
        sequence_result = pd.read_json(op.join(self.data_dir, 'sequence.json'))

        logger.debug('mutation_result: {}\n\n'.format(mutation_result))
        logger.debug('model result: {}\n\n'.format(model_result))
        logger.debug('sequence_result: {}\n\n'.format(sequence_result))

        # Remove mutations without ddg
        # (the most likely reason is that the mutation falls outside the interface)
        mutation_result = mutation_result[mutation_result['ddg'].notnull()]

        # Make the idxs column a tuple where it is not null.
        # (uniquely identifying each domain pair)
        if 'idxs' not in mutation_result.columns:
            mutation_result['idxs'] = np.nan
        else:
            mutation_result.loc[mutation_result['idxs'].notnull(), 'idxs'] = (
                mutation_result.loc[mutation_result['idxs'].notnull(), 'idxs'].apply(tuple)
            )
        if 'idxs' not in model_result.columns:
            model_result['idxs'] = np.nan
        else:
            model_result.loc[model_result['idxs'].notnull(), 'idxs'] = (
                model_result.loc[model_result['idxs'].notnull(), 'idxs'].apply(tuple)
            )

        # Create dataframes that are similar to what you would get with a query to the database
        domain_mutations = (
            mutation_result[mutation_result['idxs'].isnull()]
            .merge(model_result, on=['idx'], suffixes=('', '_model'))
            .merge(sequence_result, on=['idx'], suffixes=('', '_sequence'))
        )
        domain_pair_mutations = (
            mutation_result[mutation_result['idxs'].notnull()]
            .merge(model_result, on=['idxs'], suffixes=('', '_model'))
            .merge(sequence_result, on=['idx'], suffixes=('', '_sequence'))
        )

        mutation_results = (
            domain_mutations.to_dict(orient='records') +
            domain_pair_mutations.to_dict(orient='records')
        )
        return mutation_results


# %%
core_optional_columns_database = [
    'uniprot_id',
    'uniprot_domain_id',
    'pdbfam_name',
    'cath_id',
    'domain_def',
]

core_optional_columns_local = [
    'unique_id',
    'protein_id',
    'sequence_id',
    'structure_id',
]

core_required_columns = [
    # Info
    'core_or_interface',
    'mutation',
    'model_domain_def',
    'chain',
    'chain_modeller',

    # Features
    'alignment_coverage',
    'alignment_identity',
    'alignment_score',
    'matrix_score',
    'norm_dope',
    'physchem_mut',
    'physchem_mut_ownchain',
    'physchem_wt',
    'physchem_wt_ownchain',
    'provean_score',
    'provean_supset_length',
    'stability_energy_wt',
    'stability_energy_mut',
    'solvent_accessibility_wt',
    'solvent_accessibility_mut',
    'secondary_structure_wt',
    'secondary_structure_mut',
    'ddg',

    # Data
    'sequence',
    'sasa_score',
    'provean_supset_file',
    'provean_supset_file_2',
    'alignment_file',
    'model_file',
    'model_file_wt',
    'model_file_mut',
]


# %%
def correct_domain_mutations(df):
    # Get the main chain (1st out of 2 if there are heteroatoms)
    df['chain'] = df['chain_ids'].apply(lambda x: x[0])
    df['chain_modeller'] = df['modeller_chain_ids'].apply(lambda x: x[0])

    # ---
    def _get_model_domain_def(x):
        sequence, modeller_results = x
        domain_def_offset = modeller_results.get('domain_def_offsets', [[None, None]])[0]
        model_domain_def = get_model_domain_def(len(sequence), domain_def_offset)
        return model_domain_def

    df['model_domain_def'] = df[['sequence', 'modeller_results']].apply(
        _get_model_domain_def, axis=1)

    # ---
    def _get_sasa_score(x):
        relative_sasa_scores, chain_modeller = x
        sasa_score = relative_sasa_scores.get(chain_modeller, np.nan)
        return sasa_score

    df['sasa_score'] = df[['relative_sasa_scores', 'chain_modeller']].apply(
        _get_sasa_score, axis=1)

    # ---
    df['provean_supset_file_2'] = df['provean_supset_file'].apply(
        lambda x: x + '.fasta')
    df['alignment_file'] = df['modeller_results'].apply(
        lambda x: x.get('alignment_files', [np.nan])[0])
    df['model_file'] = df['modeller_results'].apply(
        lambda x: x.get('model_file', [np.nan])[0])


def get_model_domain_def(sequence_length, domain_def_offset=None):
    domain_start = 1
    domain_end = sequence_length
    if (domain_def_offset is None or
            domain_def_offset[0] is None or
            domain_def_offset[1] is None):
        return '{}:{}'.format(domain_start, domain_end)
    n_gaps_start, n_gaps_end = domain_def_offset
    domain_start += n_gaps_start
    domain_end -= n_gaps_end
    return '{}:{}'.format(domain_start, domain_end)


# %%
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

    return output_dict


