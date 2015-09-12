#!/bin/bash

# Make sure we know where python is installed
if [[ -z "$CONDA_INSTALL_DIR" ]] ; then
    echo '"$CONDA_INSTALL_DIR" must be set.'
    exit 1
fi
if [[ ! "$PATH" =~ "$CONDA_INSTALL_DIR" ]] ; then
    export PATH=$CONDA_INSTALL_DIR/bin:$PATH
fi

# Get Apache to play nice with Python 3
echo "export PATH=$CONDA_INSTALL_DIR/bin:$PATH" | sudo tee --append /etc/apache2/envvars
echo "umask 000" | sudo tee --append /etc/apache2/envvars

# Install mod_wsgi
MOD_WSGI=`which mod_wsgi-express`
$MOD_WSGI install-module --modules-directory /usr/lib/apache2/modules
cat <<EOF | sudo tee /etc/apache2/mods-available/wsgi.conf 
<IfModule mod_wsgi.c>
    WSGIPythonHome $CONDA_INSTALL_DIR
    WSGIPythonPath $CONDA_INSTALL_DIR/lib/python3.4/site-packages
</IfModule>
EOF
cat <<EOF | sudo tee /etc/apache2/mods-available/wsgi.load
LoadModule wsgi_module /usr/lib/apache2/modules/mod_wsgi-py34.cpython-34m.so
EOF
ln -fs ../mods-available/wsgi.conf /etc/apache2/mods-enabled/wsgi.conf
ln -fs ../mods-available/wsgi.load /etc/apache2/mods-enabled/wsgi.load

sudo service apache2 restart

