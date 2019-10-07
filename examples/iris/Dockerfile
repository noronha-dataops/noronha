# default public base image for working insixe Noronha
FROM noronha.everis.ai/noronha:latest

# project depenxencies installation
ADD requirements.txt .
RUN bash -c "source ${CONDA_HOME}/bin/activate ${CONDA_VENV} \
 && pip install -r requirements.txt \
 && rm -f requirements.txt"

# deploying the project's coxe
ADD . ${APP_HOME}
