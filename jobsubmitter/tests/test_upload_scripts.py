import os.path as op
import shlex
import subprocess

BASE_DIR = op.abspath(op.dirname(__file__))
SCRIPTS_DIR = op.abspath(op.join(BASE_DIR, '..', 'jobsubmitter', 'scripts'))
DATA_DIR = op.join(BASE_DIR, 'data')


class Test1:

    unique_id = 'nm9omiv6'
    mutations = '1_M13A'

    def test_1(self):
        system_command = (
            '{SCRIPTS_DIR}/local.py -d {DATA_DIR}/{unique_id} '
            '-u {unique_id} -t sequence'
            .format(SCRIPTS_DIR=SCRIPTS_DIR, DATA_DIR=DATA_DIR, unique_id=self.unique_id)
        )
        print(system_command)
        output = subprocess.check_output(shlex.split(system_command), universal_newlines=True)
        print(output)

    def test_2(self):
        system_command = (
            '{SCRIPTS_DIR}/local.py -d {DATA_DIR}/{unique_id} '
            '-u {unique_id} -t model'
            .format(SCRIPTS_DIR=SCRIPTS_DIR, DATA_DIR=DATA_DIR, unique_id=self.unique_id)
        )
        print(system_command)
        output = subprocess.check_output(shlex.split(system_command), universal_newlines=True)
        print(output)

    def test_3(self):
        for mutation in self.mutations.split(','):
            system_command = (
                '{SCRIPTS_DIR}/local.py -d {DATA_DIR}/{unique_id} '
                '-u {unique_id} -m {mutation} -t mutations'
                .format(SCRIPTS_DIR=SCRIPTS_DIR, DATA_DIR=DATA_DIR,
                        unique_id=self.unique_id, mutation=self.mutations)
            )
            print(system_command)
            output = subprocess.check_output(shlex.split(system_command), universal_newlines=True)
            print(output)
