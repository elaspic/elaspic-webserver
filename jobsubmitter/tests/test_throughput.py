import os.path as op
import time
import requests
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = op.abspath(op.dirname(__file__))
DATA_DIR = op.join(BASE_DIR, 'data')

url = 'http://192.168.6.201:8000/elaspic/api/1.0/'

with open(op.join(DATA_DIR, 'cosmic_missing.tsv'), 'r') as ifh:
    data = ifh.read().split('\n')


d = data[0]
data_in = [{
    'job_type': 'database',
    'protein_id': d.split('.')[0],
    'mutations': d.split('.')[1],
    'uniprot_domain_pair_ids': '',
}]
r = requests.post(url, json=data_in)
isok = 'submitted' == r.json().get('status')
print(r.json(), isok)


data = data[30000:]

# %% Single mutations
MAX_N = 30001
STEP_SIZE = 100
BATCH_SIZE = STEP_SIZE

status = {
    'isok': [],
    'notok': [],
}

stats = []
start_time = time.time()
for i in range(0, MAX_N, STEP_SIZE):
    time_diff = time.time() - start_time
    stats.append((i, time_diff))
    start_time = time.time()
    for j in range(STEP_SIZE):
        idx = i + j
        data_in = [{
            'job_type': 'database',
            'protein_id': data[110000 + idx].split('.')[0],
            'mutations': data[110000 + idx].split('.')[1],
            'uniprot_domain_pair_ids': '',
        }]
        r = requests.post(url, json=data_in)
        assert 'submitted' == r.json().get('status')


# %% All mutations
MAX_N = 30001
STEP_SIZE = 100
STEP_SIZE = 1

status = {
    'isok': [],
    'notok': [],
}

stats = []
start_time = time.time()
for i in range(0, MAX_N, STEP_SIZE):
    time_diff = time.time() - start_time
    stats.append((i, time_diff))
    start_time = time.time()
    data_in = [{
        'job_type': 'database',
        'protein_id': data[i + j].split('.')[0],
        'mutations': data[i + j].split('.')[1],
        'uniprot_domain_pair_ids': '',
    } for j in range(STEP_SIZE)]
    r = requests.post(url, json=data_in)
    assert 'submitted' == r.json().get('status')


# %%
n, time_diff = zip(*stats)

sns.set_context('notebook', font_scale=2)
sns.set_style('whitegrid')
sns.regplot(
    np.array(n[1:]), np.array([BATCH_SIZE / x for x in time_diff[1:]]),
    # scatter_kws={'color': 'r'},
    line_kws={'color': 'k', 'linewidth': 1})
plt.xlim(0, 30000)
plt.ylim(0, 300)
plt.xlabel('Number of submitted mutations')
plt.ylabel('Requests per second\n(1 mutation / request)')


# %%
stats = []
start_time = time.time()
for i in range(0, len(data), STEP_SIZE):
    time_diff = time.time() - start_time
    stats.append((i, time_diff))
    start_time = time.time()
    for j in range(STEP_SIZE):
        idx = i + j
        data_in = [{
            'job_type': 'database',
            'protein_id': data[idx].split('.')[0],
            'mutations': data[idx].split('.')[1],
            'uniprot_domain_pair_ids': '',
        }]
        r = requests.post(url, json=data_in)
        assert 'submitted' == r.json().get('status')
