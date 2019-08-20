# default public base image for working inside Noronha
FROM noronha.everis.ai/noronha:0.2.0

# project dependencies installation
ADD requirements.txt .
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} \
 && pip install -r requirements.txt \
 && rm -f requirements.txt"

# deploying the project's code
ADD . ${APP_HOME}
