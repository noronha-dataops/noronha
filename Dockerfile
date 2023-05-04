FROM debian:stretch

# OS configuration
RUN sed -i s/deb.debian.org/archive.debian.org/g /etc/apt/sources.list \
 && sed -i 's|security.debian.org|archive.debian.org/|g' /etc/apt/sources.list \
 && sed -i '/stretch-updates/d' /etc/apt/sources.list \
 && apt -y update \
 && apt -y --no-install-recommends install gnupg curl wget zip unzip bzip2 python-pip git vim \
 && apt clean \
 && rm -rf /var/lib/apt/lists/*

# environment variables
ENV AM_I_ON_BOARD Yes
ENV LOCAL_MODEL_DIR /model
ENV LOCAL_DATA_DIR /data
ENV LOG_DIR /logs
ENV APP_HOME /app
ENV CONDA_HOME /etc/miniconda
ENV CONDA_VENV py3_default

# directory structure
RUN mkdir -p ${LOCAL_MODEL_DIR}
RUN mkdir -p ${LOCAL_DATA_DIR}
RUN mkdir -p ${LOG_DIR}
RUN mkdir -p ${APP_HOME}
WORKDIR ${APP_HOME}

# installing conda
RUN wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh \
 && bash Miniconda3-latest-Linux-x86_64.sh -b -p ${CONDA_HOME} \
 && rm -rf Miniconda3-latest-Linux-x86_64.sh \
 && ln -sf ${CONDA_HOME}/bin/conda /usr/bin/conda \
 && echo ". ${CONDA_HOME}/etc/profile.d/conda.sh" >> ~/.bashrc

# creating virtual environment
RUN conda create -y --name ${CONDA_VENV} python=3.7.9

# DEV: installing requirements on advance to avoid reinstalling each time the framework's code is changed
ADD requirements ./requirements
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} && pip install -r requirements/on_board_reqs.txt"

# framework installation
ADD noronha ./noronha
ADD setup.py .
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} && pip install --no-cache-dir ."

# entrypoint configuration
ADD ./noronha/resources/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# cleaning temporary files
RUN rm -rf ./*
