# -*- coding: utf-8 -*-
"""
Created on Sun Dec  6 23:33:24 2015

@author: strokach
"""
import os
import asyncio
import os.path as op
import shlex
import re


BASE_DIR = '/home/kimlab1/database_data/elaspic_v2'
PROVEAN_LOCK_DIR = op.join(BASE_DIR, 'locks', 'sequence')
MODEL_LOCK_DIR = op.join(BASE_DIR, 'locks', 'model')
MUTATION_LOCK_DIR = op.join(BASE_DIR, 'locks', 'mutation')

QSUB_OPTIONS = {
    'sequence': {
        'run_type': 1,
        's_vmem_quota': '5650M',
        'h_vmem_quota': '5850M',
    },
    'model': {
        'run_type': 2,
        's_vmem_quota': '5650M',
        'h_vmem_quota': '5850M',
    },
    'mutation': {
        'run_type': 3,
        's_vmem_quota': '3700M',
        'h_vmem_quota': '3900M',
    }
}

DATABASE_SCRIPT = """\
#!/bin/bash
# Submission script for the ELASPIC pipeline
# Requires `input_file` to be passed in as a variable
#
#$ -S /bin/bash
#$ -N elaspic_webserver
#$ -pe smp 3
#$ -l s_rt=20:00:00
#$ -l h_rt=21:00:00
#$ -l s_vmem={s_vmem_quota}
#$ -l h_vmem={h_vmem_quota}
# # $ -l mem_free={h_vmem_quota}
# # $ -l virtual_free={h_vmem_quota}
#
#$ -cwd
#$ -o /dev/null
#$ -e /dev/null
#$ -M ostrokach@gmail.com
#$ -V
#$ -p 0

set -vs

function finish {{
  echo "The qsub bash script is terminating..."
  mv -f "{lock_filename}" "{lock_filename_finished}"
  echo "Done moving lock!"
}}
trap finish INT TERM EXIT

cd "/home/kimlab1/database_data/elaspic_v2"
mkdir -p "./pbs-output"
exec >"./pbs-output/$JOB_ID.out" 2>"./pbs-output/$JOB_ID.err"

echo `hostname`
source activate elaspic_2
elaspic -c "./config_file_mysql.ini" \
  -u "{protein_id}" -m "{mutation}" -i "{uniprot_domain_pair_ids}" -t {run_type}
"""

LOCAL_SCRIPT = """\
#!/bin/bash
# Submission script for the ELASPIC pipeline
# Requires `input_file` to be passed in as a variable
#
#$ -S /bin/bash
#$ -N elaspic_webserver
#$ -pe smp 3
#$ -l s_rt=20:00:00
#$ -l h_rt=21:00:00
#$ -l s_vmem={s_vmem_quota}
#$ -l h_vmem={h_vmem_quota}
# # $ -l mem_free={h_vmem_quota}
# # $ -l virtual_free={h_vmem_quota}
#
#$ -cwd
#$ -o /dev/null
#$ -e /dev/null
#$ -M ostrokach@gmail.com
#$ -V
#$ -p 0

set -vs

function finish {{
  echo "The qsub bash script is terminating..."
  mv -f "${lock_filename}" "${lock_filename_finished}"
  echo "Done moving lock!"
}}
trap finish INT TERM EXIT

cd "/home/kimlab1/database_data/elaspic_v2/user_input/${protein_id}"
mkdir -p "./pbs-output"
exec >"./pbs-output/$JOB_ID.out" 2>"./pbs-output/$JOB_ID.err"

echo `hostname`
source activate elaspic_2
elaspic -c "../../config_file_mysql.ini" \
    -p "{pdb_file}" -s "{sequence_file}" -m "{mutation}" -t {run_type}
"""


def get_lock_path(run_type, args, finished=False):
    """Get the name of the lock file for the given run_type.
    """
    if run_type.startswith('sequence'):
        lock_files = op.join(
            PROVEAN_LOCK_DIR,
            'finished' if finished else '',
            '{}.lock'.format(args['protein_id']))
    elif run_type.startswith('model'):
        lock_files = op.join(
            MODEL_LOCK_DIR,
            'finished' if finished else '',
            '{}.lock'.format(args['protein_id']))
    elif run_type.startswith('mutation'):
        lock_files = op.join(
            MUTATION_LOCK_DIR,
            'finished' if finished else '',
            '{}.{}.lock'.format(args['protein_id'], args['mutation']))
    else:
        raise RuntimeError
    return lock_files


@asyncio.coroutine
def watch(filename):
    """Watch a file until it is deleted.

    Can add a timeout, after which it is assumed that the job died.
    """
    while True:
        if not op.isfile(filename):
            break
        yield from asyncio.sleep(10.0)


job_cache = {}


@asyncio.coroutine
def submitjob(run_type, args, prereqs=[]):
    """Run an SGE job on the beagle cluster.

    Allow sequence (provean) and model jobs to only run once.
    """
    while not all([t.done() for t in prereqs]):
        yield from asyncio.sleep(30)

    lock_path = get_lock_path(run_type, args, finished=False)
    finished_lock_path = get_lock_path(run_type, args, finished=True)
    while True:
        if lock_path in job_cache:
            print("Found cached results for lock '{}'...".format(lock_path))
            return job_cache[lock_path]
        if op.isfile(finished_lock_path):
            print("This job is done: '{}' exits...".format(finished_lock_path))
            job_cache[lock_path] = None
            return job_cache[lock_path]
        qsub_script = DATABASE_SCRIPT if args['job_type'] == 'database' else LOCAL_SCRIPT
        qsub_script = qsub_script.format(**{
            **args,
            **QSUB_OPTIONS[run_type],
            'lock_filename': lock_path,
            'lock_filename_finished': finished_lock_path,
        })
        try:
            with open(lock_path, 'x') as ofh:
                ofh.write(qsub_script)
            print("Obtained lock on file '{}'...".format(lock_path))
            system_command = shlex.split(
                'ssh jobsubmitter@192.168.6.201 -tt qsub "{}"'.format(lock_path)
            )
            print("Running system command:\n{}".format(system_command))
            proc = yield from asyncio.create_subprocess_exec(
                *system_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            print('Submitted...')
            result, error_message = yield from proc.communicate()
            print('Communicated...')
            yield from watch(lock_path)
            print('done!')
            job_cache[lock_path] = result
            return job_cache[lock_path]
        except FileExistsError:
            print("Waiting for lock to lift: '{}'...".format(lock_path))
            yield from asyncio.sleep(30)
        except Exception as e:
            print('Unexpected exception occured!{}\n'.format(e))
            try:
                os.remove(lock_path)
            except FileNotFoundError:
                pass
        else:
            print('Making sure the lock file was removed...', sep=' ')
            try:
                os.remove(lock_path)
                print('nope!')
            except FileNotFoundError:
                print('yup!')


# %%
@asyncio.coroutine
def poison_pill(muts, loop):
    while not all([m.done() for m in muts]):
        yield from asyncio.sleep(30)


def main(args_list):
    """
    Parameters
    ----------
    args_list : list of dicts
        Each dict should have the following elements:
        - job_type  (all)
        - protein_id  (all)
        - pdb_file  (local)
        - sequence_file  (local)
        - mutations  (all)
            Can be a comma-separated list of mutations, e.g. M1A,G2A
        - uniprot_domain_pair_ids  (database)
            Comma-separated list of uniprot_domain_pair_id interfaces to analyse.
    """
    print('args_list: {}'.format(args_list))
    loop = asyncio.get_event_loop()
    muts = []
    for args in args_list:
        validate_args(args)
        s = asyncio.ensure_future(submitjob('sequence', args))
        m = asyncio.ensure_future(submitjob('sequence', args))
        for mutation in args['mutations'].split(','):
            args_mut = args.copy()
            args_mut['mutation'] = mutation
            mut = asyncio.ensure_future(submitjob('sequence', args_mut, [s, m]))
            muts.append(mut)
    asyncio.ensure_future(poison_pill(muts, loop))
    loop.run_fun_forever()


def main_old(args_list):
    """
    Parameters
    ----------
    args_list : list of dicts
        Each dict should have the following elements:
        - job_type  (all)
        - protein_id  (all)
        - pdb_file  (local)
        - sequence_file  (local)
        - mutations  (all)
            Can be a comma-separated list of mutations, e.g. M1A,G2A
        - uniprot_domain_pair_ids  (database)
            Comma-separated list of uniprot_domain_pair_id interfaces to analyse.
    """
    print('args_list: {}'.format(args_list))
    events = []
    for args in args_list:
        validate_args(args)
        for mutation in args['mutations'].split(','):
            events.append(run_mutation({**args, 'mutation': mutation}))
    print('events: {}'.format(events))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(events))


def validate_args(args):
    if args['job_type'] == 'local':
        assert all(c in args for c in ['protein_id', 'pdb_file', 'sequence_file', 'mutations'])
    elif args['job_type'] == 'database':
        assert all(c in args for c in ['protein_id', 'mutations', 'uniprot_domain_pair_ids'])
    else:
        raise RuntimeError("Wrong value for 'job_type': {}".format(args['job_type']))
    valid_reg = re.compile(r'^[\w,_-]+$')
    assert all(valid_reg.match(key) for key in args.keys())
    assert all(valid_reg.match(value) for value in args.values() if value)


# %%
if __name__ == '__main__':
    args_list = [
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
    main(args_list)
