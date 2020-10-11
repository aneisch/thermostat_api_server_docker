from python:3.8-slim-buster

RUN pip install paho-mqtt

RUN useradd thermostat_api

ENV API_SERVER_ADDRESS 10.0.1.22
ENV API_SERVER_LISTEN_PORT 8080
ENV MQTT_SERVER 127.0.0.1
ENV MQTT_PORT 1883
ENV THERMOSTAT_COMMAND_TOPIC "cmnd/thermostat/#"
ENV THERMOSTAT_STATE_TOPIC sensor/thermostat
ENV THERMOSTAT_SERIAL XXXXXXXXXXX

COPY ./thermostat_api_server.py /usr/bin/thermostat_api_server.py
RUN chmod +x /usr/bin/thermostat_api_server.py

USER thermostat_api

ENTRYPOINT python -u /usr/bin/thermostat_api_server.py
