FROM docker.bintray.io/jfrog/artifactory-cpp-ce
MAINTAINER Gustavo Castilhos <gvargasc@everis.com>

# basic OS configuration
USER root
RUN rm -f /var/lib/dpkg/lock \
 && rm -f /var/cache/apt/archives/lock \
 && rm -f /var/opt/jfrog/artifactory/.lock
