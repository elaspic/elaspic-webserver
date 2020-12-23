# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:20.04 AS build

# Suppress warnings when running apt-get
ARG DEBIAN_FRONTEND=noninteractive

# Install system requirements
RUN apt-get -qq -o=Dpkg::Use-Pty=0 update \
    && apt-get -y -qq -o=Dpkg::Use-Pty=0 install \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

RUN umask 0002 \
    && sed -ri -e 's@^UMASK[[:space:]]+[[:digit:]]+@UMASK    002@g' /etc/login.defs \
    && grep -E "^UMASK" /etc/login.defs \
    && curl -sS https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh \
    && openssl dgst -sha256 miniconda.sh | grep 1314b90489f154602fd794accfc90446111514a5a72fe1f71ab83e07de9504a7 \
    && bash miniconda.sh -b -p /opt/conda \
    && rm miniconda.sh \
    && chmod g=u /opt/conda \
    && source /opt/conda/etc/profile.d/conda.sh \
    && conda install -n base -y -q -c conda-forge -c defaults tini su-exec mamba \
    && conda clean -q -tipy -f \
    && find /opt/conda -type d -not -perm -g=rwx -exec chmod g+rwX {} + \
    && find /opt/conda -type f -not -perm -g=rw -exec chmod g+rw {} +

ARG CONDA_BLD_ARCHIVE_URL
ARG CONDA_BLD_REQUEST_HEADER
ARG PACKAGE_NAME="elaspic-webserver"
ARG PACKAGE_VERSION="0.2.1.dev0"

RUN umask 0002 \
    && mkdir /data \
    && curl -sS -L --header "${CONDA_BLD_REQUEST_HEADER}" "${CONDA_BLD_ARCHIVE_URL}" -o artifacts.zip \
    && unzip -qq artifacts.zip -d /data \
    && rm artifacts.zip \
    && source /opt/conda/etc/profile.d/conda.sh \
    && mamba create -n app -y -q -c file:///data/conda-bld -c conda-forge -c defaults -c kimlab -c ostrokach-forge -c bioconda "${PACKAGE_NAME}=${PACKAGE_VERSION}" \
    && rm -rf /data \
    && conda clean -q -tipy -f \
    && find /opt/conda -type d -not -perm -g=rwx -exec chmod g+rwX {} + \
    && find /opt/conda -type f -not -perm -g=rw -exec chmod g+rw {} +


# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:20.04

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install system requirements
RUN apt-get -qq -o=Dpkg::Use-Pty=0 update \
    && apt-get -qq -o=Dpkg::Use-Pty=0 -y install \
    file \
    && rm -rf /var/lib/apt/lists/*

RUN sed -ri -e 's@^UMASK[[:space:]]+[[:digit:]]+@UMASK    002@g' /etc/login.defs \
    && grep -E "^UMASK" /etc/login.defs \
    groupadd -g 32766 conda

# Give sudo permission for conda user to run yum (user creation is postponed
# to the entrypoint, so we can create a user with the same id as the host)
# RUN echo 'conda ALL=NOPASSWD: /usr/bin/yum' >> /etc/sudoers

RUN mkdir /opt/conda && chown root:conda /opt/conda && chmod ug=rwX,o=rX /opt/conda

COPY --chown=root:conda --from=build /opt/conda /opt/conda

RUN ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh

COPY --chown=root:conda logconfig.ini /opt/conda/share/

COPY entrypoint /opt/docker/bin/entrypoint

# Using tini prevents the following warning on container boot:
# bash: cannot set terminal process group (-1): Inappropriate ioctl for device
# bash: no job control in this shell
ENTRYPOINT [ "/opt/conda/bin/tini", "--", "/opt/docker/bin/entrypoint" ]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD [ "gunicorn", "mum.wsgi:app", \
    "--limit-request-line", "0", \
    "--log-config", "/opt/conda/share/logconfig.ini", \
    "--access-logfile", "-", "--error-logfile", "-", "--capture-output" ]
