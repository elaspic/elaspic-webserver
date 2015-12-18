#!/bin/bash

# Make sure we know where python is installed
if [[ -z "$CONDA_INSTALL_DIR" ]] ; then
    echo '"$CONDA_INSTALL_DIR" must be set!'
    exit 1
fi
if [[ ! "$PATH" =~ "$CONDA_INSTALL_DIR" ]] ; then
    export PATH=$CONDA_INSTALL_DIR/bin:$PATH
fi

# Install miniconda
if [[ ! -e "$CONDA_INSTALL_DIR/bin/python" ]] ; then
    echo "Installing Miniconda..."
    rm -rf "$CONDA_INSTALL_DIR"
    mkdir "$CONDA_INSTALL_DIR"
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh --quiet
    bash Miniconda3-latest-Linux-x86_64.sh -b -p "$CONDA_INSTALL_DIR"
    rm -f Miniconda3-latest-Linux-x86_64.sh
fi

# Add custom channels to ~/.condarc
cat <<EOF > $HOME/.condarc
channels:
  - bioconda
  - salilab
  - r
  - defaults
  - ostrokach
EOF

# Install useful conda packages
conda update -y -q conda
conda install -y -q anaconda-client
conda install -y -q conda-build jinja2 pip
pip install mod_wsgi

