FROM python:3.8-alpine as base

FROM base as builder

RUN apk add --no-cache --update py3-pip curl && \
  pip install --no-cache-dir --prefix=/install paho-mqtt

FROM base

LABEL org.opencontainers.image.source https://github.com/aneisch/thermostat_api_server_docker

HEALTHCHECK --interval=60s --timeout=5s \
  CMD curl -sLf http://localhost:8080/time || exit 1

EXPOSE 8080

COPY --from=builder /install /usr/local

ENV API_SERVER_ADDRESS 10.0.1.22
ENV MQTT_SERVER 127.0.0.1
ENV MQTT_PORT 1883
ENV THERMOSTAT_SERIAL XXXXXXXXXX
ENV THERMOSTAT_NAME Thermostat

COPY ./thermostat_api_server.py /usr/bin/thermostat_api_server.py

RUN chmod +x /usr/bin/thermostat_api_server.py && \
  adduser -D thermostat_api && \
  apk --purge del apk-tools

USER thermostat_api

ENTRYPOINT python -u /usr/bin/thermostat_api_server.py
