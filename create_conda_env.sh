#!/bin/bash

set -ex

sudo apt install apache2-dev

conda create -n mum 'python=3.5' elaspic django
source activate mum
pip install mod_wsgi aiohttp aiomysql

