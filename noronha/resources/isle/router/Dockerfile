FROM node

ADD package.json .

RUN npm install

RUN mkdir -p /logs

ADD router.js .

ENTRYPOINT ["node", "router.js"]
