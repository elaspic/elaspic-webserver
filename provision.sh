#!/bin/bash

set -ev

# Jobsubmitter
rsync -rv --chown=9284:7300 ~/mum/jobsubmitter/scripts/ /home/kimlab1/database_data/elaspic_v2/scripts/

sudo supervisorctl restart all


# ELASPIC
python ~/mum/manage.py collectstatic --noinput -i download -i jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic_v2/webserver/jobs \
    /var/www/elaspic.kimlab.org/static/jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic.kimlab.org \
    /var/www/elaspic.kimlab.org/static/download

sudo service apache2 restart

