FROM docker.bintray.io/jfrog/artifactory-oss
MAINTAINER Gustavo Castilhos <gvargasc@everis.com>

# basic OS configuration
USER root
RUN rm -f /var/lib/dpkg/lock \
 && rm -f /var/cache/apt/archives/lock \
 && rm -f /var/opt/jfrog/artifactory/.lock

# tomcat configuration
RUN sed -i 's/Connector/Connector connectionTimeout="120000"/' /opt/jfrog/artifactory/tomcat/conf/server.xml
