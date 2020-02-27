# default public base image for working inside Noronha
FROM noronha.everis.ai/noronha:develop

# project dependencies installation
ADD requirements.txt .
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} \
 && conda install --file requirements.txt"

# deploying the project's code
ADD . ${APP_HOME}
