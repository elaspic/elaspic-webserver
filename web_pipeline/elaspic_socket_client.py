# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 16:04:01 2015

@author: strokach
"""

import socket
import json
import logging


def jsonize(fn):
    """
    Convert a function that takes as input and returns as output **binary json data**
    to a function that takes as input and returns as output **dictionaries**.
    """
    def jsonized_fn(input_data=None):
        if input_data is not None:
            input_data = json.dumps(input_data).encode('utf-8')
        output_data = fn(input_data)
        if output_data is not None:
            output_data = json.loads(output_data.decode())
        return output_data
    return jsonized_fn
    

class JobSubmitter(object):
    
    def __init__(self, ip='192.168.6.201', port=59462, logger=logging):
        self.ip = ip
        self.port = port
        self.logger = logger
        self.logger.info('Working with elaspic jobsubmitter on %s:%s...', ip, port)
        

    def submitjob(self, uniprot_id, mutations):
        message = {'request': 'submitjob', 'uniprot_id': uniprot_id, 'mutations': mutations}
        return jsonize(self._send_message)(message)
    
    
    def check_progress(self, uniprot_id, mutations):
        message = {'request': 'check_progress', 'uniprot_id': uniprot_id, 'mutations': mutations}
        return jsonize(self._send_request)(message)

    
    def jobstatus(self, job_id, full=False):
        message = {'job_id': job_id}
        if not full:
            message['request'] = 'jobstatus'
        else:
            message['request'] = 'jobstatus_full'
        return jsonize(self._send_request)(message)


    def _send_message(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            self.logger.debug('sending message: "{}"'.format(message))
            s.send(message)


    def _send_request(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            self.logger.debug('sending request: "{}"'.format(message))
            s.send(message)
            response_all = b''
            while True:
                response = s.recv(1024)
                if not response:
                    break
                response_all += response
            self.logger.debug('response from server: "{}"'.format(response_all))
        return response_all




if __name__ == '__main__':
    js = JobSubmitter()

    uniprot_id = 'P35372'
    mutation = 'N386A'
    mutation = 'P65A,V94A,T209P'

    uniprot_id = 'Q9VN38'
    mutation = 'C369A'
   
    uniprot_id = 'P10608'
    mutation = 'H256A'
    
    # Mouse
    uniprot_id = 'Q9D067'
    mutation = 'K338A'
    mutation = 'Q228A,A283C,N369A'
    mutation = 'Q521A'
    
    uniprot_id = 'P23804'
    mutation = 'L81A'
    mutation = 'C303A,C317A'
    mutation = 'V449A,Q481A'
    
    job = js.submitjob(uniprot_id, mutation)
    
    print(js.check_progress(uniprot_id, mutation))
    
    jobstatus = js.jobstatus(job['job_id'])
    print(jobstatus)
    
    jobstatus_full = js.jobstatus(job['job_id'], full=True)
    for key, value in jobstatus_full.items():
        print('#' * 100)
        print(key)
        print(value)
        
    jobstatus_full = js.jobstatus(2345, full=False)
    for key, value in jobstatus_full.items():
        print('#' * 100)
        print(key)
        print(value)