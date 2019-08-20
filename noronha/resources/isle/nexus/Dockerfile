FROM sonatype/nexus3
MAINTAINER Gustavo Castilhos <gvargasc@everis.com>

# basic OS configuration
USER root
RUN rm -f /var/lib/dpkg/lock \
 && rm -f /var/cache/apt/archives/lock
