# ELASPIC Webserver

- [Installation](#installation)
- [Folders](#folders)

## Installation

Install required libraries:

```
sudo apt install apache2-dev postfix  # to send mail
```

## Python requirements

```bash
conda create -n elaspic-webserver 'python>=3.6' django kmtools aiohttp requests mysqlclient redis redis-py sqlalchemy
source activate elaspic-webserver
pip install aiomysql aioredis raven
```

For testing:

```bash
pip install flake8 pytest pytest-logging pytest-cov pytest-asyncio
```


Create conda environment:

```
conda env create -f environment.yml
```

If you already have the conda environment from a previous release, you can update using:

```
conda env update -f environment.yml
```

For jobsubmitter:

```
aiohttp aiomysql pytest pytest-asyncio
```

## Folders

### [conf](/conf)

This folder contains apache and supervisord configuration files.

### [deploy](/deploy)

This folder contains obsolete scripts for configuring vagrant and docker images.

### [jobsubmitter](/jobsubmitter)

Asynchronous web server for submitting and monitoring ELASPIC jobs in the SGE cluster.

### [mum](/mum)

MUM configurations and settings.

### [notebooks](/notebooks)

Notebooks with examples and tests.

### [web_pipeline](/web_pipeline)

MUM app.
