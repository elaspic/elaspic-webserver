#!/bin/bash

# Make sure we know where python is installed
if [[ -z "$CONDA_INSTALL_DIR" ]] ; then
    echo '"$CONDA_INSTALL_DIR" must be set.'
    exit 1
fi
if [[ ! "$PATH" =~ "$CONDA_INSTALL_DIR" ]] ; then
    export PATH=$CONDA_INSTALL_DIR/bin:$PATH
fi

# Install required packages
conda install -y elaspic
pip install mod_wsgi 
pip install django django-celery

# Copy webserver code
python $HOME/mum/manage.py collectstatic --noinput
ln -nsf /home/kimlab1/database_data/elaspic.kimlab.org $HOME/mum/static/download

# Add mod_wsgi configuration file to Apache
sudo rm -f /etc/apache2/sites-enabled/000-default*
sudo cp -f $HOME/mum/_install/elaspic_webserver.conf /etc/apache2/sites-available
sudo ln -s -f ../sites-available/elaspic_webserver.conf /etc/apache2/sites-enabled/elaspic_webserver.conf
sudo service apache2 restart

# Install rabit-mq server
#if ! grep "deb http://www.rabbitmq.com/debian/ testing main" /etc/apt/sources.list ; then
#    echo "deb http://www.rabbitmq.com/debian/ testing main" | sudo tee --append /etc/apt/sources.list
#    wget https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
#    apt-key add rabbitmq-signing-key-public.asc
#    rm rabbitmq-signing-key-public.asc
#fi
#sudo apt-get update
sudo apt-get install rabbitmq-server

# Add celery configurations to Supervisor
mkdir -p $HOME/mum/log/elaspic
mkdir -p $HOME/mum/log/celery
sudo ln -sf $HOME/mum/_install/celeryd.conf /etc/supervisor/conf.d/celeryd.conf  
sudo ln -sf $HOME/mum/_install/celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf 
sudo service supervisor stop
sleep 1
sudo service supervisor start
# Show which process is blocking supervisord from starting
if [[ $? -ne 0 ]] ; then
    sudo netstat -atn
    sudo unlink /var/run/supervisor.sock
    sleep 1
    sudo service supervisor start
fi

