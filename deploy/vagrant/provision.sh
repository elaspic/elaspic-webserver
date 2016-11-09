#!/usr/bin/env bash

DEBIAN_FRONTEND=noninteractive

## This should not be required with a newer packer script
rm -r /var/lib/apt/lists/*

## Install system packages
apt-get update
apt-get install -y vim git

# Postfix
debconf-set-selections <<< "postfix postfix/mailname string your.hostname.com"
debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
apt-get install -y postfix

# Apache
apt-get install -y apache2 apache2-dev libxml2 libxml2-dev

# Supervisor
apt-get install -y supervisor
# for remote access with nodevisor
if ! grep 'port = *:9009' /etc/supervisor/supervisord.conf ; then
    cat <<EOF >> /etc/supervisor/supervisord.conf

[inet_http_server]
port = *:9009 ;

EOF
fi

## Set environment variables
USER=kimadmin
export CONDA_INSTALL_DIR=/home/$USER/miniconda
export PATH="$CONDA_INSTALL_DIR/bin:$PATH"

if ! grep CONDA_INSTALL_DIR /home/$USER/.profile ; then
    cat <<EOF >> /home/$USER/.profile
### Custom changes ###
export CONDA_INSTALL_DIR="$CONDA_INSTALL_DIR"
export PATH="\$CONDA_INSTALL_DIR/bin:\$PATH"
export KEY_MODELLER="***REMOVED***"
EOF
fi


## Mount folders
apt-get install -y nfs-common sshfs

mkdir -p /home/kimlab1/database_data/blast
mkdir -p /home/kimlab1/database_data/elaspic_v2
mkdir -p /home/kimlab1/database_data/elaspic.kimlab.org

if ! grep "/home/kimlab1/database_data/blast" /etc/fstab >/dev/null; then
    sudo echo "192.168.6.8:/kimlab1/database_data/blast /home/kimlab1/database_data/blast nfs rw,vers=3,hard,intr,noatime,rsize=32768,wsize=32768 0 2"  >> /etc/fstab
fi
if ! grep "/home/kimlab1/database_data/elaspic_v2" /etc/fstab >/dev/null; then
    sudo echo "sshfs#jobsubmitter@192.168.6.201:/home/kimlab1/database_data/elaspic_v2    /home/kimlab1/database_data/elaspic_v2    fuse    cache=yes,kernel_cache,compression=no,Ciphers=arcfour,allow_other,IdentityFile=/home/kimadmin/.ssh/id_rsa,ServerAliveInterval=60    0    0"  >> /etc/fstab
fi
if ! grep "/home/kimlab1/database_data/elaspic.kimlab.org" /etc/fstab >/dev/null; then
    sudo echo "sshfs#jobsubmitter@192.168.6.201:/home/kimlab1/database_data/elaspic.kimlab.org    /home/kimlab1/database_data/elaspic.kimlab.org    fuse    cache=yes,kernel_cache,compression=no,Ciphers=arcfour,allow_other,IdentityFile=/home/kimadmin/.ssh/id_rsa,ServerAliveInterval=60    0    0"  >> /etc/fstab
fi

sudo mount --all


## Install Python
su -c "source /vagrant/install_python.sh" $USER -l

## Configure apache with mod_wsgi
#su -c "CONDA_INSTALL_DIR=$CONDA_INSTALL_DIR source /vagrant/configure_apache.sh" 
su -c "source /vagrant/configure_apache.sh" $USER -l

## Install all packages required by the webserver (including mod_wsgi)
su -c "source /vagrant/install_webserver.sh" $USER -l

