#!/bin/bash

set -ex

sudo apt install apache2-dev postfix  # to send mail

conda create -n elaspic_webserver 'python=3.5' elaspic django mysqlclient
source activate elaspic_webserver
pip install mod_wsgi aiohttp aiomysql pytest pytest-asyncio

