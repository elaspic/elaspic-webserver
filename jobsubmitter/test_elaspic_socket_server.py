# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 16:54:36 2015

@author: strokach
"""

import subprocess
import pytest
import elaspic_socket_server as f



def test_check_precalculated():
    
    uniprot_id = 'P10608'
    assert f.check_precalculated(uniprot_id) == (True, True)


def test__validate_message_dict():
    # 
    message_dict = {'uniprot_id': 'P01625', 'mutations': 'N34F,V91F'}
    assert f._validate_message_dict(message_dict) is None
    # 
    message_dict = {'uniprot_id': 'P01xxxxx625', 'mutations': 'V91F'}
    assert f._validate_message_dict(message_dict) is None
    # 
    message_dict = {'uniprot_id': 'rm *', 'mutations': '*'}
    with pytest.raises(f.BadMessageException):
        assert f._validate_message_dict(message_dict)
    #
    message_dict = {'uniprot_id': 'cat /etc/passwd', 'mutations': 'echo ~/.ssh/.key'}
    with pytest.raises(f.BadMessageException):
        assert f._validate_message_dict(message_dict)


def test__submit_job():
    # 
    assert f._submitjob("echo \"Life is good!\"") == "Life is good!\n"
    # 
    assert f._submitjob("sleep 9") == ''
    #
    with pytest.raises(FileNotFoundError):
        assert f._submitjob("xxx")
    # 
    with pytest.raises(subprocess.CalledProcessError):
        assert f._submitjob("test 0 == 1")
    # 
    with pytest.raises(subprocess.TimeoutExpired):
        f._submitjob("sleep 11")


def test__extract_job_id():
    # 
    output = 'Your job 3259443 ("elaspic") has been submitted'
    assert f._extract_job_id(output) == 3259443
    # 
    output = 'Your job 3259,443 ("elaspic") has been submitted'
    with pytest.raises(f.BadJobIDException):
        f._extract_job_id(output)
    # 
    output = ''
    with pytest.raises(f.BadJobIDException):
        f._extract_job_id(output)


if __name__ == '__main__':
    pytest.main()