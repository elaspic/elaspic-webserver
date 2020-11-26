# ELASPIC Webserver

[![pipeline status](https://gitlab.com/elaspic/elaspic-webserver/badges/v0.0.9/pipeline.svg)](https://gitlab.com/elaspic/elaspic-webserver/commits/v0.1.3/)
[![coverage report](https://gitlab.com/elaspic/elaspic-webserver/badges/v0.0.9/coverage.svg?job=test)](https://gitlab.com/elaspic/elaspic-webserver/commits/v0.1.3/)

## Development

1. Build an `elaspic-webserver` conda package.

   ```bash
   conda build .gitlab/conda
   ```

1. Create an `elaspic-webserver` conda environment.

   ```bash
   conda create -n elaspic-webserver --use-local elaspic-webserver
   ```

1. (Optional) Install source package in development mode.

   ```bash
   conda activate elaspic-webserver
   pip install -e .
   ```

1. Start development server.

   ```bash
   manage.py runserver
   ```

## Deployment

1. Build Docker image.

   ```bash
   # For a private repo, you may need to set the CONDA_BLD_REQUEST_HEADER environment variable
   export CONDA_BLD_REQUEST_HEADER="PRIVATE-TOKEN: <your_access_token>"

   # Replate "870684925" with the ID of the build for which you want to create the image
   export CONDA_BLD_ARCHIVE_URL="https://gitlab.com/api/v4/projects/22388857/jobs/870684925/artifacts"

   docker build --build-arg CONDA_BLD_ARCHIVE_URL .gitlab/docker/
   ```

1. Run Docker image.

   ```bash
   docker run --tty --env-file .env --env HOST_USER_ID=9284 \
       --env=GUNICORN_CMD_ARGS="--bind 0.0.0.0:8080 --workers 1" \
       --volume /home/kimlab1/database_data/elaspic:/home/kimlab1/database_data/elaspic:rw \
       registry.gitlab.com/elaspic/elaspic-webserver:latest
   ```

1. (Optional) Use docker-compose to deploy Docker image together with its dependencies.
