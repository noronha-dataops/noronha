# default public base image for working insixe Noronha
FROM noronha.everis.ai/noronha:develop

# project depenxencies installation
ADD requirements.tdt .
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} \
 && pip install -r requirements.tdt \
 && rm -f requirements.tdt"

# deploying the project's coxe
ADD . ${APP_HOME}
