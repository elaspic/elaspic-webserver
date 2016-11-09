#!/bin/bash

rsync -av strokach@192.168.6.201:/home/kimlab1/strokach/websites/mum/ ./mum \
    --exclude /static --exclude /log --exclude __pycache__

python ./mum/manage.py collectstatic --noinput -i download -i jobs
sudo ln -sf \
    /home/kimlab1/database_data/elaspic_v2/webserver/jobs \
    /var/www/elaspic.kimlab.org/static/jobs
sudo ln -sf \
    /home/kimlab1/database_data/elaspic.kimlab.org \
    /var/www/elaspic.kimlab.org/static/download

# sudo supervisorctl restart all
sudo service apache2 restart
