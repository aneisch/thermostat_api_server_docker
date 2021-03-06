from python:3.8-alpine

LABEL org.opencontainers.image.source https://github.com/aneisch/thermostat_api_server_docker

HEALTHCHECK --interval=60s --timeout=5s \
  CMD curl -sLf http://localhost:8080/time || exit 1
  
EXPOSE 8080

RUN apk add --no-cache --update py3-pip curl
RUN pip install paho-mqtt

RUN adduser -D thermostat_api

ENV API_SERVER_ADDRESS 10.0.1.22
ENV MQTT_SERVER 127.0.0.1
ENV MQTT_PORT 1883
ENV THERMOSTAT_COMMAND_TOPIC "cmnd/thermostat/#"
ENV THERMOSTAT_STATE_TOPIC sensor/thermostat
ENV THERMOSTAT_SERIAL XXXXXXXXXXX

COPY ./thermostat_api_server.py /usr/bin/thermostat_api_server.py
RUN chmod +x /usr/bin/thermostat_api_server.py

USER thermostat_api

ENTRYPOINT python -u /usr/bin/thermostat_api_server.py
