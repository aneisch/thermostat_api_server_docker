#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqttClient
import datetime
import os
import socketserver
import time
import json
import logging

logging.basicConfig(
    level=os.environ['LOG_LEVEL'], format="%(asctime)s -- %(levelname)s -- %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

candidate_configuration = {"hold": "on", "fan": "auto"}
current_configuration = {}
changes_pending = False
first_start = True

api_server_address = os.environ['API_SERVER_ADDRESS']
mqtt_address = os.environ['MQTT_SERVER']
mqtt_port = int(os.environ['MQTT_PORT'])
if 'MQTT_USERNAME' in os.environ:
  mqtt_username = os.environ['MQTT_USERNAME']
  mqtt_password = os.environ['MQTT_PASSWORD']
thermostat_name = os.environ['THERMOSTAT_NAME']
thermostat_command_topic = f"homeassistant/climate/{thermostat_name}/cmnd"
thermostat_state_topic = f"homeassistant/climate/{thermostat_name}/state"
thermostat_serial = os.environ['THERMOSTAT_SERIAL']

device = {"mdl": "TSTAT0201CW", "mf": "Observer", "ids": thermostat_serial, "name": thermostat_name}

climate_configuration_payload = {
    "act_t": thermostat_state_topic,
    "act_tpl": "{% if value_json.coolicon == 'on' %}cooling{% elif value_json.heaticon == 'on' %}heating{% elif value_json.coolicon == 'off' and value_json.heaticon == 'off' %}idle{% endif %}",
    "curr_temp_t": thermostat_state_topic,
    "curr_temp_tpl": "{{ value_json.rt }}",
    "device": device,
    "fan_modes": ["auto","low","med","high"],
    "fan_mode_cmd_t": thermostat_command_topic + "/fan_mode",
    "fan_mode_stat_t": thermostat_state_topic,
    "fan_mode_stat_tpl": "{{ value_json.fan }}",
    "max_temp": 85,
    "min_temp": 55,
    "mode_cmd_t": thermostat_command_topic + "/operating_mode",
    "mode_stat_t": thermostat_state_topic,
    "mode_stat_tpl": "{{ value_json.mode }}",
    "modes": ["off", "cool", "heat"],
    "name": thermostat_name,
    "temp_cmd_t": thermostat_command_topic + "/temperature",
    "temp_stat_t": thermostat_state_topic,
    "temp_stat_tpl": "{% if value_json.mode == 'cool' %}{{ value_json.clsp }}{% elif value_json.mode == 'heat' %}{{ value_json.htsp }}{% endif %}",
    "temp_step":"1",
    "temperature_unit": "F",
    "uniq_id": thermostat_serial
}

def on_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT")
    client.subscribe(f"{thermostat_command_topic}/#")
    logging.info(f'''Subscribed to {thermostat_command_topic}/#''')

    client.publish(f'homeassistant/climate/{thermostat_serial}-climate/config', json.dumps(climate_configuration_payload), retain=True)

    latest_equipment_event_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Active Equipment Event",
        "ic": "mdi:alert",
        "val_tpl": "{{ value_json.latest_equip }}",
        "uniq_id": f"{thermostat_serial}-latest-equip"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-latest-equip/config', json.dumps(latest_equipment_event_payload), retain=True)

    temperature_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Temperature",
        "unit_of_meas": "°F",
        "ic": "mdi:thermometer",
        "val_tpl": "{{ value_json.rt }}",
        "uniq_id": f"{thermostat_serial}-temp"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-temp/config', json.dumps(temperature_sensor_configuration_payload), retain=True)

    humidity_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Humidity",
        "unit_of_meas": "%",
        "ic": "mdi:water-percent",
        "val_tpl": "{{ value_json.rh }}",
        "uniq_id": f"{thermostat_serial}-humidity"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-humidity/config', json.dumps(humidity_sensor_configuration_payload), retain=True)

    mode_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Operating Mode",
        "ic": "mdi:home-thermometer",
        "val_tpl": "{{ value_json.mode }}",
        "uniq_id": f"{thermostat_serial}-mode"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-modee/config', json.dumps(mode_sensor_configuration_payload), retain=True)

    fan_mode_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Fan Mode",
        "val_tpl": "{{ value_json.fan }}",
        "ic": "mdi:fan",
        "uniq_id": f"{thermostat_serial}-fan-mode"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-fan-mode/config', json.dumps(fan_mode_sensor_configuration_payload), retain=True)

    state_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} State",
        "ic": "mdi:home-thermometer",
        "val_tpl": "{% if value_json.coolicon == 'on' %}Cooling{% elif value_json.heaticon == 'on' %}Heating{% elif value_json.fanicon == 'on' %}Idle Fan{% elif value_json.coolicon == 'off' and value_json.heaticon == 'off' and value_json.fanicon == 'off' %}Idle{% else %}Unknown{% endif %}",
        "uniq_id": f"{thermostat_serial}-state"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-state/config', json.dumps(state_sensor_configuration_payload), retain=True)

    setpoint_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Setpoint",
        "ic": "mdi:thermometer",
        "val_tpl": "{% if value_json.mode == 'cool' %}{{ value_json.clsp }}{% elif value_json.mode == 'heat' %}{{ value_json.htsp }}{% endif %}",
        "uniq_id": f"{thermostat_serial}-setpoint",
        "unit_of_meas": "°F"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-setpoint/config', json.dumps(setpoint_sensor_configuration_payload), retain=True)

    fanicon_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Fan Status",
        "val_tpl": "{{ value_json.fanicon }}",
        "ic": "mdi:fan",
        "uniq_id": f"{thermostat_serial}-fanicon"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-fan-status/config', json.dumps(fanicon_sensor_configuration_payload), retain=True)

    hold_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Hold",
        "val_tpl": "{{ value_json.hold }}",
        "ic": "mdi:gesture-tap-hold",
        "uniq_id": f"{thermostat_serial}-hold"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-hold/config', json.dumps(hold_sensor_configuration_payload), retain=True)

    filtrlvl_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Filter Hours Remain",
        "ic": "mdi:clock",
        "val_tpl": "{{ value_json.filtrlvl }}",
        "uniq_id": f"{thermostat_serial}-filtrlvl",
        "unit_of_meas": "h",
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-filtrlvl/config', json.dumps(filtrlvl_sensor_configuration_payload), retain=True)

    oducoiltmp_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Outdoor Coil Temperature",
        "ic": "mdi:hvac",
        "val_tpl": "{{ value_json.oducoiltmp }}",
        "uniq_id": f"{thermostat_serial}-oducoiltmp",
        "unit_of_meas": "°F"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-oducoiltmp/config', json.dumps(oducoiltmp_sensor_configuration_payload), retain=True)

    oat_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Outdoor Ambient Temperature",
        "ic": "mdi:thermometer",
        "val_tpl": "{{ value_json.oat }}",
        "uniq_id": f"{thermostat_serial}-oat",
        "unit_of_meas": "°F"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-oat/config', json.dumps(oat_sensor_configuration_payload), retain=True)

    iducfm_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "name": f"{thermostat_name} Indoor CFM",
        "ic": "mdi:fan",
        "val_tpl": "{{ value_json.iducfm }}",
        "uniq_id": f"{thermostat_serial}-iducfm",
        "unit_of_meas": "cfm"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-iducfm/config', json.dumps(iducfm_sensor_configuration_payload), retain=True)

    last_time_sensor_configuration_payload = {
        "device": device,
        "stat_t": thermostat_state_topic,
        "val_tpl": "{{ value_json.last_communication }}",
        "name": f"{thermostat_name} Last Communication",
        "ic": "mdi:clock",
        "uniq_id": f"{thermostat_serial}-last-time"
    }
    client.publish(f'homeassistant/sensor/{thermostat_serial}-last-time/config', json.dumps(last_time_sensor_configuration_payload), retain=True)

    logging.info('Published Config Entries')

def on_message(client, userdata, message):
    global changes_pending
    global candidate_configuration
    message.payload = message.payload.decode("utf-8")
    logging.info(f'''New message: {message.topic} {message.payload}''')

    if message.topic == f"{thermostat_command_topic}/operating_mode":
        new_operating_mode = message.payload
        changes_pending = True
        candidate_configuration["mode"] = new_operating_mode

    elif message.topic == f"{thermostat_command_topic}/fan_mode":
        new_fan_mode = message.payload
        changes_pending = True
        candidate_configuration["fan"] = new_fan_mode

    elif message.topic == f"{thermostat_command_topic}/hold":
        new_hold_mode = message.payload
        changes_pending = True
        candidate_configuration["hold"] = new_hold_mode

    elif message.topic == f"{thermostat_command_topic}/temperature":
        new_temperature = message.payload

        if 'clsp' in candidate_configuration:
            if candidate_configuration['mode'] == "cool" and new_temperature != candidate_configuration['clsp']:
                changes_pending = True
                candidate_configuration["clsp"] = new_temperature.split(".")[0]

        if 'htsp' in candidate_configuration:
            if candidate_configuration['mode'] == "heat" and new_temperature != candidate_configuration['htsp']:
                changes_pending = True
                candidate_configuration["htsp"] = new_temperature.split(".")[0]

class MyHttpRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send_no_changes(self):
        html = f'''<status version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/status"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><pingRate>0</pingRate><dealerConfigPingRate>0</dealerConfigPingRate><weatherPingRate>14400</weatherPingRate><equipEventsPingRate>60</equipEventsPingRate><historyPingRate>86400</historyPingRate><iduFaultsPingRate>86400</iduFaultsPingRate><iduStatusPingRate>86400</iduStatusPingRate><oduFaultsPingRate>86400</oduFaultsPingRate><oduStatusPingRate>0</oduStatusPingRate><configHasChanges>off</configHasChanges><dealerConfigHasChanges>off</dealerConfigHasChanges><dealerHasChanges>off</dealerHasChanges><oduConfigHasChanges>off</oduConfigHasChanges><iduConfigHasChanges>off</iduConfigHasChanges><utilityEventsHasChanges>off</utilityEventsHasChanges></status>'''
        self.send_response(200)
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Connection", "keep-alive")
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(bytes(html, "utf8"))

    def send_empty_200(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        html = ""

        if "/Alive" in self.path:
            html = "alive"
            self.send_response(200)
            self.send_header("Content-Length", "5")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        elif "/time" in self.path:
            time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            html = f'''<time version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/time/"/><utc>{time}</utc></time>'''
            self.send_response(200)
            self.send_header("Content-Length", len(html))
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        elif "/config" in self.path:
            global changes_pending
            changes_pending = False
            logging.info(f'''New configuration: {candidate_configuration}''')
            html = f'''<config version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/config"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><atom:link rel="http://{api_server_address}/rels/dealer_config" href="http://{api_server_address}/systems/{thermostat_serial}/dealer_config"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><mode>{candidate_configuration["mode"]}</mode><fan>{candidate_configuration["fan"]}</fan><blight>10</blight><timeFormat>12</timeFormat><dst>on</dst><volume>high</volume><soundType>click</soundType><scrLockout>off</scrLockout><scrLockoutCode>0000</scrLockoutCode><humSetpoint>45</humSetpoint><dehumSetpoint>45</dehumSetpoint><utilityEvent/><zones><zone id="1"><name>Zone 1</name><hold>{candidate_configuration["hold"]}</hold><otmr/><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp><program></program></zone></zones></config>'''
            self.send_response(200)
            self.send_header("Content-Length", len(html))
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        else:
            # Send 0 length 200 response
            self.send_empty_200()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get('Content-length'))).decode("utf-8")
        data = unquote(data).strip("data=")
        global current_configuration
        global candidate_configuration
        global first_start

        html = ""
        match = False

        monitored = ["rt","rh","mode","fan","coolicon","heaticon","fanicon","hold","filtrlvl","clsp","htsp","opstat","iducfm","oat","oducoiltmp"]
        paths = ["/status", "/odu_status","/equipment_events"] # we only need data from these paths
        received_message = {}

        final_locator = f'/{self.path.split("/")[-1:][0]}' # eg /status

        if len(data) >= 45 and final_locator in paths:
            logging.debug(f"{final_locator} -- {data}")
            try: 
                # Parse and create dict of received message
                root = ET.fromstring(data)
                children = list(root)
                if "/equipment_events" in final_locator:
                    for child in root.iter():
                        # Only get latest equipment event
                        if child.tag in received_message:
                            continue
                        else:
                            received_message[child.tag] = child.text
                else:
                    for child in root.iter():
                        received_message[child.tag] = child.text
            except:
                if "/status" in self.path:
                    self.send_no_changes()
                else:
                    self.send_empty_200
                return

            # Build current_configuration with monitored variables
            for option in monitored:
                if option in received_message:
                    current_configuration[option] = received_message[option]

            # We don't need any kind of response for this path
            if "/odu_status" in final_locator:
                self.send_empty_200()

            elif "/equipment_events" in final_locator:
                if received_message['active'] == "on":
                    state = f"{received_message['localtime'][1:]}: {received_message['description']}"
                else:
                    state = "No Active Event"
                current_configuration["latest_equip"] = state
                self.send_empty_200()

            elif "/status" in final_locator:
                logging.debug(f"{current_configuration}")
                current_configuration["last_communication"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                # Initialize candidate_configuration as current_configuration at first start
                if first_start == True:
                    candidate_configuration['clsp'] = current_configuration['clsp']
                    candidate_configuration['htsp'] = current_configuration['htsp']
                    candidate_configuration['mode'] = current_configuration['mode']

                    # Update climate device with client IP
                    climate_configuration_payload["device"]["cns"] = [["ip", self.client_address[0]]]
                    client.publish(f'homeassistant/climate/{thermostat_serial}-climate/config', json.dumps(climate_configuration_payload), retain=True)
                
                    first_start = False
                    self.send_no_changes()

                elif changes_pending == True:
                    logging.info("Responding with change notice...")
                    html = f'''<status version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/status"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><pingRate>0</pingRate><dealerConfigPingRate>0</dealerConfigPingRate><weatherPingRate>14400</weatherPingRate><equipEventsPingRate>60</equipEventsPingRate><historyPingRate>86400</historyPingRate><iduFaultsPingRate>86400</iduFaultsPingRate><iduStatusPingRate>86400</iduStatusPingRate><oduFaultsPingRate>86400</oduFaultsPingRate><oduStatusPingRate>0</oduStatusPingRate><configHasChanges>on</configHasChanges><dealerConfigHasChanges>off</dealerConfigHasChanges><dealerHasChanges>off</dealerHasChanges><oduConfigHasChanges>off</oduConfigHasChanges><iduConfigHasChanges>off</iduConfigHasChanges><utilityEventsHasChanges>off</utilityEventsHasChanges></status>'''
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(html)))
                    self.send_header("Content-Type", "application/xml; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(bytes(html, "utf8"))

                else:
                    self.send_no_changes()

            # Update MQTT topic with current states
            client.publish(thermostat_state_topic, str(current_configuration).replace("'",'"').replace("None",'""'), retain=True)

        # Malformed message
        else:
            if "/status" in self.path:
                self.send_no_changes()

            else:
                # Send 0 length 200 response
                self.send_empty_200()

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

client = mqttClient.Client(f"thermostat_api_server_{thermostat_serial}")
if "mqtt_username" in locals():
  client.username_pw_set(username=mqtt_username,password=mqtt_password)
server = ThreadingSimpleServer(('0.0.0.0', 8080), MyHttpRequestHandler)

client.on_connect = on_connect
client.on_message = on_message
logging.info("Connecting to MQTT")
client.connect(mqtt_address, mqtt_port)

client.loop_start()
client.subscribe(thermostat_command_topic)
server.serve_forever()
