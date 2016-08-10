#!/bin/bash

conda create -n mum 'python=3.5' elaspic django
source activate -n mum
pip install mod_wsgi aiohttp aiomysql

