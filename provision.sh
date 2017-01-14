#!/bin/bash

read -p "This will replace your configuration files! Are you sure? " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    # handle exits from shell or function but don't exit interactive shell:
    [[ "$0" == "$BASH_SOURCE" ]] && exit 1 || return 1
fi

set -ev


# Jobsubmitter

rsync -rv --chown=9284:7300 ~/mum/jobsubmitter/scripts/ /home/kimlab1/database_data/elaspic/scripts/

sudo rsync -av ./conf/jobsubmitter.conf /etc/supervisor/conf.d/jobsubmitter.conf

sudo supervisorctl reload
sudo supervisorctl reread
sudo supervisorctl restart jobsubmitter


# ELASPIC

python ~/mum/manage.py collectstatic --noinput -i download -i jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic/webserver/jobs \
    /var/www/elaspic.kimlab.org/static/jobs

sudo ln -snf \
    /home/kimlab1/database_data/elaspic.kimlab.org \
    /var/www/elaspic.kimlab.org/static/download


# Apache

sudo rsync -av ./conf/elaspic_webserver.conf /etc/apache2/sites-available/elaspic_webserver.conf
sudo ln -sf '../sites-available/elaspic_webserver.conf' '/etc/apache2/sites-enabled/elaspic_webserver.conf'

sudo service apache2 restart
