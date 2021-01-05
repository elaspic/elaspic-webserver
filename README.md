# ELASPIC Webserver

[![pipeline status](https://gitlab.com/elaspic/elaspic-webserver/badges/v0.2.6.dev0/pipeline.svg)](https://gitlab.com/elaspic/elaspic-webserver/commits/v0.1.3/)
[![coverage report](https://gitlab.com/elaspic/elaspic-webserver/badges/v0.2.6.dev0/coverage.svg?job=test)](https://gitlab.com/elaspic/elaspic-webserver/commits/v0.1.3/)

## Development

1. Build an `elaspic-webserver` conda package.

   ```bash
   conda build .gitlab/conda
   ```

1. Create an `elaspic-webserver` conda environment using the built package (this will automatically install all dependencies).

   ```bash
   conda create -n elaspic-webserver --use-local elaspic-webserver
   ```

1. (Optional) Install source package in development mode.

   ```bash
   conda activate elaspic-webserver
   pip install -e .
   ```

1. Start the development server.

   ```bash
   conda activate elaspic-webserver
   manage.py runserver
   ```

## Deployment

1. Build a Docker image.

   ```bash
   export CONDA_BLD_ARCHIVE_URL="https://gitlab.com/api/v4/projects/3259401/jobs/artifacts/master/download?job=build"

   docker build --build-arg CONDA_BLD_ARCHIVE_URL .gitlab/docker/
   ```

1. Run the built Docker image.

   ```bash
   docker run --tty --env-file .env --env HOST_USER_ID=9284 \
       --env=GUNICORN_CMD_ARGS="--bind 0.0.0.0:8080 --workers 3" \
       --volume /home/kimlab1/database_data/elaspic:/home/kimlab1/database_data/elaspic:rw \
       registry.gitlab.com/elaspic/elaspic-webserver:latest
   ```

1. (Optional) Use docker-compose to deploy the built Docker image together with its dependencies.
