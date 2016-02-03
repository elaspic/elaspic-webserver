# -*- coding: utf-8 -*-
"""
Created on Tue Dec 15 13:42:14 2015

@author: strokach
"""
import os
import os.path as op
import shlex
import re
import time
import logging
import subprocess
import smtplib
import asyncio
import aiomysql
from email.mime.text import MIMEText
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
import sh

import config

# For sendEmail
from web_pipeline import functions

logger = logging.getLogger(__name__)
loop = asyncio.get_event_loop()
executor = ThreadPoolExecutor()


# %% Parameters
JOB_TIMEOUT = 24 * 60 * 60  # 24 hours

SLEEP_FOR_DB = 60
SLEEP_FOR_INFO = 60
SLEEP_FOR_QSTAT = 30
SLEEP_FOR_ERROR = 5
SLEEP_FOR_QSUB = 0.01
SLEEP_FOR_LOOP = 0.01

DATA_DIR = '/home/kimlab1/database_data/elaspic_v2'
DB_SCHEMA = 'elaspic_webserver'

# SCRIPTS_DIR is for beagle01
# SCRIPTS_DIR = op.join(config.BASE_DIR, 'scripts')
SCRIPTS_DIR = '/home/kimlab1/jobsubmitter/mum/jobsubmitter/scripts'
PROVEAN_LOCK_DIR = op.join(DATA_DIR, 'locks', 'sequence')
MODEL_LOCK_DIR = op.join(DATA_DIR, 'locks', 'model')
MUTATION_LOCK_DIR = op.join(DATA_DIR, 'locks', 'mutation')

JOB_ID_RE = re.compile('^Your job (\d.*) \(.*$')

SSH_STRING = (
    '' if sh.hostname().strip() == 'beagle01'
    else 'ssh jobsubmitter@192.168.6.201 '
)


# %% SGE
QSUB_OPTIONS = {
    'sequence': {
        'elaspic_run_type': 1,
        'num_cores': 1,
        's_rt': '23:30:00',
        'h_rt': '24:00:00',
        's_vmem': '24G',
        'h_vmem': '24G',
        'args': [
            '-pe', 'smp', '1',
            '-l', 's_rt=23:30:00',
            '-l', 'h_rt=24:00:00',
            '-l', 's_vmem=5650M',
            '-l', 'h_vmem=5850M',
        ],
    },
    'model': {
        'elaspic_run_type': 2,
        'num_cores': 1,
        's_rt': '23:30:00',
        'h_rt': '24:00:00',
        's_vmem': '24G',
        'h_vmem': '24G',
        'args': [
            '-pe', 'smp', '1',
            '-l', 's_rt=23:30:00',
            '-l', 'h_rt=24:00:00',
            '-l', 's_vmem=5650M',
            '-l', 'h_vmem=5850M',
        ],
    },
    'mutations': {
        'elaspic_run_type': 3,
        'num_cores': 1,
        's_rt': '23:30:00',
        'h_rt': '24:00:00',
        's_vmem': '12G',
        'h_vmem': '12G',
        'args': [
            '-pe', 'smp', '1',
            '-l', 's_rt=23:30:00',
            '-l', 'h_rt=24:00:00',
            '-l', 's_vmem=5650M',
            '-l', 'h_vmem=5850M',
        ],
    }
}

QSUB_SYSTEM_COMMAND = """\
qsub -pe smp {num_cores} -l s_rt={s_rt} -l h_rt={h_rt} -l s_vmem={s_vmem} -l h_vmem={h_vmem} \
-v lock_filename="{lock_filename}" -v lock_filename_finished="{lock_filename_finished}" \
-v protein_id="{protein_id}" -v mutations="{mutations}" \
-v uniprot_domain_pair_ids="{uniprot_domain_pair_ids}" \
-v structure_file="{structure_file}" \
-v sequence_file="{sequence_file}" \
-v SCRIPTS_DIR="{SCRIPTS_DIR}" \
-v run_type={run_type} -v elaspic_run_type={elaspic_run_type} \
{SCRIPTS_DIR}/{job_type}.sh \
"""


# %% Helper functions
def get_unique_id(run_type, args):
    unique_id = '.'.join([args['job_type'], run_type, args['protein_id']])
    if run_type == 'mutations':
        unique_id += '.' + args['mutations']
    return unique_id


def get_lock_path(run_type, args, finished=False):
    """Get the name of the lock file for the given run_type.
    """
    if run_type == 'sequence':
        lock_files = op.join(
            PROVEAN_LOCK_DIR,
            'finished' if finished else '',
            '{}.lock'.format(args['protein_id']))
    elif run_type == 'model':
        lock_files = op.join(
            MODEL_LOCK_DIR,
            'finished' if finished else '',
            '{}.lock'.format(args['protein_id']))
    elif run_type == 'mutations':
        lock_files = op.join(
            MUTATION_LOCK_DIR,
            'finished' if finished else '',
            '{}.{}.lock'.format(args['protein_id'], args['mutations']))
    else:
        raise RuntimeError
    return lock_files


def get_log_paths(job_type, job_id, protein_id):
    if job_type == 'database':
        # Database
        args = dict(data_dir=DATA_DIR, job_id=job_id)
        stdout_path = "{data_dir}/pbs-output/{job_id}.out".format(**args)
        stderr_path = "{data_dir}/pbs-output/{job_id}.err".format(**args)
    else:
        # Local
        args = dict(data_dir=DATA_DIR, protein_id=protein_id, job_id=job_id)
        stdout_path = "{data_dir}/user_input/{protein_id}/pbs-output/{job_id}.out".format(**args)
        stderr_path = "{data_dir}/user_input/{protein_id}/pbs-output/{job_id}.err".format(**args)
    return stdout_path, stderr_path


def send_email(item, system_command, restarting=False):
    """
    TODO: Rework this to be asyncronous.
    """
    me = 'no-reply@kimlab.org'
    you = 'ostrokach@gmail.com'
    body = []
    body.extend([
        'A job with job id {} did not run successfully!'
        .format(item.job_id, JOB_TIMEOUT // 60 // 60),
        "It can be restarted with the following system commad:\n'{}'"
        .format(system_command),
        "The log files can be found here:\n{}\n{}\n"
        .format(item.stdout_path, item.stderr_path),
    ])
    restarting = 'Restarting...' if restarting else 'Failed!'
    message = '\n'.join(body)
    msg = MIMEText(message)
    msg['Subject'] = (
        'ELASPIC job {} ({}) failed. {}'.format(item.job_id, item.unique_id, restarting)
    )
    msg['From'] = me
    msg['To'] = you
    s = smtplib.SMTP('localhost')
    s.sendmail(me, [you], msg.as_string())
    s.quit()


def remove_from_monitored_jobs(item):
    if item.args.get('webserver_job_id'):
        job_key = (item.args.get('webserver_job_id'), item.args.get('webserver_job_email'))
        logger.debug(
            "Removing unique_id '{}' from monitored_jobs with key '{}..."
            .format(item.unique_id, job_key)
        )
        try:
            monitored_jobs[job_key].remove(item.unique_id)
            logger.debug('Removed!')
        except KeyError:
            logger.debug('Key does not exist!')


# %% Helper classes
class JobTimeoutError:
    pass


class Item:

    def __init__(self, run_type, args):
        self.run_type = run_type
        self.args = args
        self.init_time = time.time()
        #
        self.qsub_tries = 0
        self.validation_tries = 0
        self.unique_id = get_unique_id(run_type, args)
        self.lock_path = get_lock_path(run_type, args, finished=False)
        self.finished_lock_path = get_lock_path(run_type, args, finished=True)
        self.prereqs = []
        if run_type == 'mutations':
            self.prereqs = [
                '{job_type}.sequence.{protein_id}'.format(**args),
                '{job_type}.model.{protein_id}'.format(**args),
            ]
        #
        self.job_id = None
        self.stdout_path = None  # need_job_id
        self.stderr_path = None  # need job_id

    def set_job_id(self, job_id):
        self.job_id = job_id
        self.start_time = time.time()
        self.stdout_path, self.stderr_path = (
            get_log_paths(self.args['job_type'], self.job_id, self.args['protein_id'])
        )


# %% Job cache
precalculated = dict()
precalculated_cache = dict()

async def get_precalculated():
    global precalculated
    logger.debug('get_precalculated')
    async with aiomysql.connect(
            host='192.168.6.19', port=3306, user='elaspic', password='elaspic',
            db='elaspic', loop=loop) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, job_id from jobsubmitter_cache;")
            values = await cur.fetchall()
            precalculated = {v[0]: v[1] for v in values}

loop.run_until_complete(get_precalculated())


async def persist_precalculated():
    while True:
        logger.debug('persist_precalculated')
        if not precalculated_cache:
            await asyncio.sleep(SLEEP_FOR_DB)
            continue
        try:
            async with aiomysql.connect(
                    host='192.168.6.19', port=3306, user='elaspic', password='elaspic',
                    db='elaspic', loop=loop) as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        "INSERT INTO jobsubmitter_cache (id, job_id) values (%s,%s) "
                        "ON DUPLICATE KEY UPDATE job_id=job_id;",
                        list(precalculated_cache.items())
                    )
                    await conn.commit()
                    # Update global variables
                    precalculated.update(precalculated_cache)
                    precalculated_cache.clear()
        except Exception as e:
            error_message = (
                'The following error occured while trying to persist data to the database:\n{}'
                .format(e)
            )
            logger.error(error_message)
            await asyncio.sleep(SLEEP_FOR_ERROR)
            continue
        await asyncio.sleep(SLEEP_FOR_DB)

loop.create_task(persist_precalculated())


async def set_job_status(j):
    """
    Copy-paste from web_pipeline.functions, so that I don't have to laod all database models.
    """
    job_id, job_email = j
    # Update database
    async with aiomysql.connect(
            host='192.168.6.19', port=3306, user='elaspic-web', password='elaspic',
            db=DB_SCHEMA, loop=loop) as conn:
        async with conn.cursor() as cur:
            db_command = (
                "update jobs "
                "set isDone = 1, dateFinished = now() "
                "where jobID = '{}';"
                .format(job_id)
            )
            logger.debug('Executing the following db command:\n{}'.format(db_command))
            await cur.execute(db_command)
        await conn.commit()


async def set_db_errors(error_queue):
    logger.debug('set_db_errors: '.format(error_queue))

    async def helper(cur, item):
        remove_from_monitored_jobs(item)
        protein_id = item.args['protein_id']
        mutation = item.args['mutations'].split('_')[-1]
        db_command = (
            "CALL update_muts('{}', '{}')"
            .format(item.args['protein_id'], item.args['mutations'])
        )
        logger.debug(db_command)
        await cur.execute(db_command)

    async with aiomysql.connect(
            host='192.168.6.19', port=3306, user='elaspic-web', password='elaspic',
            db=DB_SCHEMA, loop=loop) as conn:
        async with conn.cursor() as cur:
            try:
                if isinstance(error_queue, asyncio.Queue):
                    while not error_queue.empty():
                        item = await error_queue.get()
                        await helper(cur, item)
                else:
                    for item in error_queue:
                        await helper(cur, item)
                await conn.commit()
            except Exception as e:
                logger.error(
                    'The following error occured while trying to send errors to the database:\n{}'
                    .format(e)
                )


# %% qstat
running_jobs = set()
running_jobs_last_updated = 0
validation_last_updated = 0
monitored_jobs = defaultdict(set)

validation_queue = asyncio.Queue()
qsub_queue = asyncio.Queue()
pre_qsub_queue = asyncio.Queue()


async def get_stats():
    while True:
        logger.info('*' * 50)
        logger.info('{:40}{:10}'.format('Submitted jobs:', len(running_jobs)))
        logger.info('{:40}{:10}'.format('validation_queue:', validation_queue.qsize()))
        logger.info('{:40}{:10}'.format('qsub_queue:', qsub_queue.qsize()))
        logger.info('{:40}{:10}'.format('pre_qsub_queue:', pre_qsub_queue.qsize()))
        # logger.debug('precalculated: {}'.format(precalculated))
        logger.info('precalculated_cache: {}'.format(precalculated_cache))
        logger.info('*' * 50)
        await asyncio.sleep(SLEEP_FOR_INFO)

loop.create_task(get_stats())


async def qstat():
    global running_jobs
    global running_jobs_last_updated
    while True:
        logger.debug('qstat')
        system_command = SSH_STRING + "qstat -u 'jobsubmitter'"
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(system_command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        result, error_message = await proc.communicate()
        result = result.decode()
        if error_message:
            logger.error(
                "system command: '{}', error message: '{}'"
                .format(system_command, error_message)
            )
            await asyncio.sleep(SLEEP_FOR_ERROR)
            continue
        running_jobs = {
            int(x.split(' ')[0])
            for x in result.split('\n')
            if x and x.split(' ')[0].isdigit()
        }
        running_jobs_last_updated = time.time()
        await asyncio.sleep(SLEEP_FOR_QSTAT)

loop.create_task(qstat())


# %%
async def finalize_finished_jobs():
    while True:
        logger.debug('finalize_finished_jobs')
        logger.debug('monitored_jobs: {}'.format(monitored_jobs))
        if monitored_jobs:
            finished_jobs = []
            for job_key, job_set in monitored_jobs.items():
                if not job_set:
                    logger.debug("monitored_jobs with key '{}' is empty, finalizing..."
                                 .format(monitored_jobs))
                    if job_key[1]:  # job email was specified
                        executor.submit(functions.sendEmail, job_key, 'complete')
                    await set_job_status(job_key)
                    finished_jobs.append(job_key)
                    await asyncio.sleep(SLEEP_FOR_LOOP)
            for job_key in finished_jobs:
                monitored_jobs.pop(job_key)
        await asyncio.sleep(SLEEP_FOR_QSTAT)

loop.create_task(finalize_finished_jobs())


async def validation():
    """Validate finished jobs.
    """
    global validation_last_updated
    while True:
        for _ in range(validation_queue.qsize()):
            logger.debug('validation')
            item = await validation_queue.get()
            #
            if (item.start_time > running_jobs_last_updated) or (item.job_id in running_jobs):
                logger.debug('Job not ready for validation')
                await validation_queue.put(item)
                await asyncio.sleep(SLEEP_FOR_LOOP)
                continue
            #
            validation_passphrase = 'Finished successfully'
            system_command = 'grep "{}" {}'.format(validation_passphrase, item.stdout_path)
            logger.debug(system_command)
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(system_command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            result, error_message = await proc.communicate()
            result = result.decode()
            error_message = error_message.decode()
            validated = validation_passphrase in result
            logger.debug('validated: {}'.format(validated))
            if validated:
                if item.run_type in ['sequence', 'model']:
                    logger.debug('Adding finished job {} to cache...'.format(item.job_id))
                    precalculated_cache[item.unique_id] = item.job_id
                    logger.debug('precalculated_cache: {}'.format(precalculated_cache))
                message = (
                    "Making sure the lock file '{}' has been removed... "
                    .format(item.lock_path)
                )
                try:
                    os.remove(item.lock_path)
                    logger.debug(message + 'nope!')
                except FileNotFoundError:
                    logger.debug(message + 'yup!')
                remove_from_monitored_jobs(item)
            else:
                logger.error('Failed to validate with system command:\n{}'.format(system_command))
                restarting = (
                    (item.validation_tries < 5) &
                    (abs(time.time() - item.start_time) < JOB_TIMEOUT)
                )
                send_email(item, system_command, restarting)
                logger.debug('Removing the lock file...')
                try:
                    os.remove(item.lock_path)
                    logger.debug('nope!')
                except FileNotFoundError:
                    logger.debug('yup!')
                if restarting:
                    logger.error('Restarting...')
                    item.validation_tries += 1
                    await qsub_queue.put(item)
                else:
                    logger.error('Out of time. Skipping...')
                    await set_db_errors([item])
            await asyncio.sleep(SLEEP_FOR_LOOP)
        await asyncio.sleep(SLEEP_FOR_QSTAT)

loop.create_task(validation())


async def qsub():
    """Submit jobs.
    """
    while True:
        logger.debug('qsub')
        item = await qsub_queue.get()
        #
        if (item.run_type in ['sequence', 'model'] and
                item.unique_id in precalculated_cache or item.unique_id in precalculated):
            logger.debug("Item '{}' already calculated. Skipping...".format(item.unique_id))
            continue
        #
        try:
            open(item.lock_path, 'x').close()
            system_command = SSH_STRING + QSUB_SYSTEM_COMMAND.format(**{
                **item.args,
                **QSUB_OPTIONS[item.run_type],
                'run_type': item.run_type,
                'lock_filename': item.lock_path,
                'lock_filename_finished': item.finished_lock_path,
                'SCRIPTS_DIR': SCRIPTS_DIR
            })
            logger.debug("Running system command:\n{}".format(system_command))
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(system_command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            result, error_message = await proc.communicate()
            result = result.decode()
            error_message = error_message.decode()
            job_id = JOB_ID_RE.findall(result)
            logger.debug('job_id: {}'.format(job_id))

            if len(job_id) == 1 and job_id[0].isdigit():
                job_id = int(job_id[0])
                item.set_job_id(job_id)
                await validation_queue.put(item)
            else:
                job_id = None
                logger.error(
                    "Submitting job with system command '{}' produced no job id "
                    "and the following results: '{}' and error: '{}'"
                    .format(system_command, result, error_message))
                restarting = item.qsub_tries < 5
                if restarting:
                    logger.error('Restarting...')
                    item.qsub_tries += 1
                    await qsub_queue.put(item)
                else:
                    logger.error('Too many restarts. Skipping...')
                    await set_db_errors([item])
        except FileExistsError:
            logger.debug("Item '{}' already being calculated. Skipping...".format(item.unique_id))
            await asyncio.sleep(SLEEP_FOR_QSUB)
            continue

        except Exception as e:
            logger.error('Unexpected exception occured!\n{}: {}'.format(type(e), e))
            try:
                os.remove(item.lock_path)
            except FileNotFoundError:
                pass
            await asyncio.sleep(SLEEP_FOR_ERROR)
            restarting = item.qsub_tries < 5
            if restarting:
                logger.error('Restarting...')
                item.qsub_tries += 1
                await qsub_queue.put(item)
            else:
                logger.error('Too many restarts. Skipping...')
                await set_db_errors([item])
        #
        await asyncio.sleep(SLEEP_FOR_QSUB)

loop.create_task(qsub())

lsd = deque(maxlen=512)


def check_prereqs(prereqs):
    have_prereqs = True
    for prereq in prereqs:
        if prereq in lsd:
            continue
        elif prereq in precalculated_cache or prereq in precalculated:
            lsd.appendleft(prereq)
            continue
        else:
            have_prereqs = False
            break
    return have_prereqs


async def pre_qsub():
    """Wait while the sequence and model prerequisites are being calculated.
    """

    while True:
        for _ in range(pre_qsub_queue.qsize()):
            logger.debug('pre_qsub')
            item = await pre_qsub_queue.get()
            have_prereqs = check_prereqs(item.prereqs)
            if not have_prereqs:
                logger.debug('Waiting for prereqs: {}'.format(item.prereqs))
                restarting = abs(time.time() - item.init_time) < JOB_TIMEOUT
                if restarting:
                    await pre_qsub_queue.put(item)
                else:
                    await set_db_errors([item])
            else:
                await qsub_queue.put(item)
            await asyncio.sleep(SLEEP_FOR_LOOP)
        await asyncio.sleep(SLEEP_FOR_QSTAT)

loop.create_task(pre_qsub())


async def cleanup():
    """
    """
    await set_db_errors(validation_queue)
    await set_db_errors(qsub_queue)
    await set_db_errors(pre_qsub_queue)
    system_command = (
        'bash -c "rm -f \"/home/kimlab1/database_data/elaspic_v2/locks/*/*.lock\""'
    )
    subprocess.check_output(shlex.split(system_command))


# %% Main
async def main(data_in):
    """
    Parameters
    ----------
    data_in : list of dicts
        Each dict should have the following elements:
        - job_type  (all)
        - protein_id  (all)
        - structure_file  (local)
        - sequence_file  (local)
        - mutations  (all)
            Can be a comma-separated list of mutations, e.g. M1A,G2A
        - uniprot_domain_pair_ids  (database)
            Comma-separated list of uniprot_domain_pair_id interfaces to analyse.
    """
    if not isinstance(data_in, (list, tuple)):
        data_in = [data_in]
    for args in data_in:
        logger.debug('main')
        validate_args(args)
        logger.debug('done validating args')
        have_prereqs = True
        # sequence
        s = Item(run_type='sequence', args=args)
        if not check_prereqs([s.unique_id]):
            await qsub_queue.put(s)
            have_prereqs = False
        # model
        m = Item(run_type='model', args=args)
        if not check_prereqs([m.unique_id]):
            await qsub_queue.put(m)
            have_prereqs = False
        # mutations
        job_mutations = set()
        for mutation in args['mutations'].split(','):
            args1 = args.copy()
            args1['mutations'] = mutation
            mut = Item(run_type='mutations', args=args1)
            if have_prereqs:
                await qsub_queue.put(mut)
            else:
                await pre_qsub_queue.put(mut)
            job_mutations.add(mut.unique_id)
        if args.get('webserver_job_id') and job_mutations:
            job_key = (args.get('webserver_job_id'), args.get('webserver_job_email'))
            monitored_jobs[job_key].update(job_mutations)


def validate_args(args):
    logger.debug('validate_args')
    # Make sure the job_type is specified and fail gracefully if it isn't
    if 'job_type' not in args:
        reason = (
            "Don't know whether running a local or a database mutation. args:\n{}"
            .format(args)
        )
        # raise aiohttp.web.HTTPBadRequest(reason=reason)
        raise Exception(reason)
    #
    if 'job_id' in args and 'webserver_job_id' not in args:
        args['webserver_job_id'] = args['job_id']
    if 'job_email' in args and 'webserver_job_email' not in args:
        args['webserver_job_email'] = args['job_email']

    # Fill in defaults:
    args['sequence_file'] = args.get('sequence_file', None)
    args['uniprot_domain_pair_ids'] = args.get('uniprot_domain_pair_ids', None)
    # Make sure we have all the required arguments for the given job type
    if args['job_type'] == 'local':
        local_opts = [
            'protein_id', 'mutations', 'structure_file', 'sequence_file'
        ]
        if not all(c in args for c in local_opts):
            reason = (
                "Wrong arguments for '{}' jobtype:\n{}".format(args['job_type'], args)
            )
            # raise aiohttp.web.HTTPBadRequest(reason=reason)
            raise Exception(reason)
    elif args['job_type'] == 'database':
        database_opts = [
            'protein_id', 'mutations', 'uniprot_domain_pair_ids'
        ]
        args['structure_file'] = args.get('structure_file', None)
        if not all(c in args for c in database_opts):
            reason = (
                "Wrong arguments for '{}' jobtype:\n{}".format(args['job_type'], args)
            )
            # raise aiohttp.web.HTTPBadRequest(reason=reason)
            raise Exception(reason)
    # This has been causing nothing but problems...
#    # Sanitize our inputs
#    valid_reg = re.compile(r'^[\w,_-@]+$')
#    if not all(valid_reg.match(key) for key in args.keys()):
#        logger.debug('Bad request keys')
#        # raise aiohttp.web.HTTPBadRequest()
#        raise Exception(reason)
#    if not all(valid_reg.match(value) for value in args.values() if value):
#        logger.debug('Bad request values')
#        # raise aiohttp.web.HTTPBadRequest()
#        raise Exception(reason)


# %%
if __name__ == '__main__':
    import logging.config
    config.LOGGING_CONFIGS['loggers']['']['handlers'] = ['default']
    logging.config.dictConfig(config.LOGGING_CONFIGS)
    logger.debug('hello')
    data_in = [
        {
            'job_type': 'database',
            'protein_id': 'P21397',
            'mutations': 'G49V,G49A,G49L,G49I,G49C,G49M,G49F,G49W,G49P',
            'uniprot_domain_pair_ids': '',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'O00522',
            'mutations': 'L526C',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'P09391',
            'mutations': 'Y138F,Y160F,Q226A,W241A,E134A,L229A,L143A,S269V,Y205A,L200A,A206G,V203A,'
                         'D243A,F139A,F146A,Q190A,P95A,M247A,F197A,M100A,W236G,L184A,F153A,M144A,'
                         'A253V,C104A,L179A,L155A,M120A,P219A,G202A,R168A,H141A,S221A,L174A,W158F,'
                         'Q112A,D218A,T178A,G209V,G199A,G215V,L207A,C104V,I180A,G194V,L169A,M111A,'
                         'S147A,R214A,T140A,I177A,G198V',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'Q8ZRU4',
            'mutations': 'M407A,V136A',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'Q8Z9H0',
            'mutations': 'P355A,E246A,A415C',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'P0A910',
            'mutations': 'Y150A,F144A,W78A,Y76A,F72A,F191A,Y189A,G49A,W164A,Y64A,Y162A,W36A',
        }, {
            'job_type': 'database',
            'uniprot_domain_pair_ids': '',
            'protein_id': 'P0A921',
            'mutations': 'A243R,Y234A,A230T,A230V,A230P,G232L,G232A,A230S,G232R,L140R,Y234L,A230W,'
                         'A230R,A230Y,Y234R,A230Q,A243L,L140A',
        }
    ]
    asyncio.ensure_future(main(data_in))
    print('Done calling main')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
