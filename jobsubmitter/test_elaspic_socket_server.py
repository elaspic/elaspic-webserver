# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 16:54:36 2015

@author: strokach
"""

import os
import string
import random
import tempfile
import logging

import pandas as pd

import pytest
import elaspic_socket_server as f


f.TESTING = True
f.LOG_DIR = tempfile.mkdtemp()


# TODO: This part is not used at the moment
columns = ['uniprot_id', 'mutations', 'valid', 'provean_missing', 'model_missing', 'have_domains']

data = [
    ('P01625', 'N34F,V91F', True, False, False, 1,),
    ('P01xxxxx625', 'V91F', False, False, False, 0,),
    ('P01625', 'N34F,V91F', False, False, False, 1,),
]

test_df = pd.DataFrame(data=data, columns=columns)



@pytest.mark.first
def test_get_logger():
    test_input = [
        ('P01625', 'N34F,V91F'),
    ]
    for uniprot_id, mutations in test_input:
        logger_filename = f._get_logger_filename(f._get_logger_name(uniprot_id, mutations))
                
        logger = f.get_logger(uniprot_id, mutations)
        assert isinstance(logger, logging.Logger)

        random_string = ''.join(
            string.ascii_letters[random.randint(0, len(string.ascii_letters)-1)]
            for i in range(100)
        )
        logger.info(random_string)
        with open(logger_filename) as ifh:
            assert random_string in ifh.read()


def test__validate_message_dict():
    # 
    message_dict = {'request': 'a', 'uniprot_id': 'P01625', 'mutations': 'N34F,V91F'}
    assert f._validate_message_dict(message_dict) is None
    # 
    message_dict = {'request': 'b', 'uniprot_id': 'P01xxxxx625', 'mutations': 'V91F'}
    assert f._validate_message_dict(message_dict) is None
    # No request
    with pytest.raises(f.BadMessageException):
        message_dict = {'uniprot_id': 'P01625', 'mutations': 'N34F,V91F'}
        f._validate_message_dict(message_dict)
    # Unsafe uniprot_id / mutation
    message_dict = {'request': 'c', 'uniprot_id': 'rm *', 'mutations': '*'}
    with pytest.raises(f.BadMessageException):
        assert f._validate_message_dict(message_dict)
    # Unsafe uniprot_id / mutation
    message_dict = {'request': 'd', 'uniprot_id': 'cat /etc/passwd', 'mutations': 'echo ~/.ssh/.key'}
    with pytest.raises(f.BadMessageException):
        assert f._validate_message_dict(message_dict)


def test_jobsubmitter():
    test_input = [
        ('P01625', 'N34F,V91F', (False, False, 1,)),
        ('P01xxxxx625', 'V91F', (False, False, 0,)),
        ('', '', (False, False, 0,)),    
    ]
    for uniprot_id, mutations, output in test_input:
        ep = f.ElaspicPipeline(uniprot_id, mutations)
        _remove_lock_files(ep)
        ep.jobsubmitter()


def _remove_lock_files(ep):
    lock_files = [
        ep.lock_filename(run_type, finished)
        for run_type in ['p', 'm', 'mut']
        for finished in [False, True]
    ]
    for lock_file in lock_files:
        try:
            os.remove(lock_file)
        except FileNotFoundError:
            pass


def test_check_precalculated():
    test_input = [
        ('P01625', 'N34F,V91F', (False, False, 1,)),
        ('P01xxxxx625', 'V91F', (False, False, 0,)),
        ('', '', (False, False, 0,)),    
    ]
    for uniprot_id, mutations, output in test_input:
        ep = f.ElaspicPipeline(uniprot_id, mutations)
        assert ep.check_precalculated() == output


def test_check_progress():
    test_input = [
        ('P01625', 'N34F,V91F', (False, False, 1,)),
        ('P01xxxxx625', 'V91F', (False, False, 0,)),
        ('', '', (False, False, 0,)),    
    ]
    for uniprot_id, mutations, output in test_input:
        ep = f.ElaspicPipeline(uniprot_id, mutations)
        output_dict = ep.check_progress()
        assert output_dict['status'] == 'Done'


if __name__ == '__main__':
    #pytest.main()
    pytest.main(['--cov','elaspic_socket_server'], plugins=['pytest-cov'])