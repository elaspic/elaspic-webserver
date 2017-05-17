#!/bin/bash

set -ex

if [ "$(id -u)" == "0" ]; then
    echo "This script must not be run as root!"
    exit 1
fi

# Jobsubmitter

sudo rsync -av ./conf/jobsubmitter.conf /etc/supervisor/conf.d/jobsubmitter.conf

sudo supervisorctl reload
sudo supervisorctl reread
sudo supervisorctl restart jobsubmitter

# ELASPIC

DJANGO_SETTINGS_MODULE='mum.settings.production' /home/kimadmin/miniconda/envs/elaspic-webserver/bin/python manage.py collectstatic --noinput -i download -i jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic/webserver/jobs \
    /var/www/elaspic.kimlab.org/static/jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic.kimlab.org \
    /var/www/elaspic.kimlab.org/static/download

# Apache

sudo rsync -av ./conf/elaspic_webserver.conf /etc/apache2/sites-available/elaspic_webserver.conf

pushd /etc/apache2/sites-enabled/
  sudo ln -sf ../sites-available/elaspic_webserver.conf
popd

sudo service apache2 restart

