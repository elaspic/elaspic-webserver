#!/usr/bin/env bash

## This should not be required with a newer packer script
rm -r /var/lib/apt/lists/*

## Install system packages
apt-get update
apt-get install -y nfs-common
apt-get install -y vim git

# Apache
apt-get install -y apache2 apache2-dev

# RabbitMQ
apt-get install -y rabbitmq-server

# Supervisor
apt-get install -y supervisor
# for remote access with nodevisor
if ! grep 'port = *:9009' /etc/supervisor/supervisord.conf ; then
    cat <<EOF >> /etc/supervisor/supervisord.conf

[inet_http_server]
port = *:9009 ;

EOF
fi

## Node.js
#apt-get install -y nodejs nodejs-legacy npm node-sax node-debug node-xml2js


## Set environment variables
USER=kimadmin
export CONDA_INSTALL_DIR=/home/$USER/miniconda3
export PATH="$CONDA_INSTALL_DIR/bin:$PATH"

if ! grep CONDA_INSTALL_DIR /home/$USER/.profile ; then
    cat <<EOF >> /home/$USER/.profile
### Custom changes ###
export CONDA_INSTALL_DIR="$CONDA_INSTALL_DIR"
export PATH="\$CONDA_INSTALL_DIR/bin:\$PATH"
EOF
fi


## Mount folders
apt-get install nfs-common

mount_folder () {
    local MOUNT_FOLDER=$1
    local FSTAB_LINE="192.168.6.8:${MOUNT_FOLDER} /home${MOUNT_FOLDER} nfs rw,vers=3,hard,intr,noatime,rsize=32768,wsize=32768 0 2"
    mount "/home${MOUNT_FOLDER}" 1>/dev/null 2>&1
    if [[ "$?" -ne "0" && "$?" -ne "32" ]] ; then
        echo "Adding line '$FSTAB_LINE' to '/etc/fstab'..."
        mkdir -p "/home${MOUNT_FOLDER}"
        echo "$FSTAB_LINE" | tee --append /etc/fstab
        mount "/home${MOUNT_FOLDER}"
    fi
}

mount_folder '/kimlab1/database_data/elaspic.kimlab.org'
mount_folder '/kimlab1/database_data/elaspic_v2'
mount_folder '/kimlab1/database_data/blast'

## Install Python
su -c "source /vagrant/install_python.sh" $USER -l

## Configure apache with mod_wsgi
su -c "CONDA_INSTALL_DIR=$CONDA_INSTALL_DIR source /vagrant/configure_apache.sh" 

## Install all packages required by the webserver (including mod_wsgi)
su -c "source /vagrant/install_webserver.sh" $USER -l


