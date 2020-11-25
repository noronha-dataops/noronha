FROM debian:stretch

# basic OS configuration
RUN apt-get -y update \
 && apt-get -y install gnupg

# MongoDB installation
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4 \
 && echo "deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/4.0 main" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list \
 && apt-get -y update \
 && ln -s /bin/true /usr/local/bin/systemctl \
 && apt-get -y install mongodb-org \
 && cp /lib/systemd/system/mongod.service /etc/init.d/mongod \
 && chmod +x /etc/init.d/mongod

ENTRYPOINT ["mongod"]
