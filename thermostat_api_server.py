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

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

candidate_configuration = {"hold": "on", "fan": "auto"}
current_configuration = {}
changes_pending = False
first_start = True

api_server_address = os.environ['API_SERVER_ADDRESS']
api_server_listen_port = int(os.environ['API_SERVER_LISTEN_PORT'])
mqtt_address = os.environ['MQTT_SERVER']
mqtt_port = int(os.environ['MQTT_PORT'])
thermostat_command_topic = os.environ['THERMOSTAT_COMMAND_TOPIC']
thermostat_state_topic = os.environ['THERMOSTAT_STATE_TOPIC']
thermostat_serial = os.environ['THERMOSTAT_SERIAL']

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT")
    client.subscribe(thermostat_command_topic)
    print(f'''Subscribed to {thermostat_command_topic}''')

def on_message(client, userdata, message):
    global changes_pending
    global candidate_configuration
    message.payload = message.payload.decode("utf-8")
    print(f'''New message: {message.topic} {message.payload}''')

    if message.topic == "cmnd/thermostat/operating_mode":
        new_operating_mode = message.payload
        changes_pending = True
        candidate_configuration["mode"] = new_operating_mode

    elif message.topic == "cmnd/thermostat/fan_mode":
        new_fan_mode = message.payload
        changes_pending = True
        candidate_configuration["fan"] = new_fan_mode

    elif message.topic == "cmnd/thermostat/hold":
        new_hold_mode = message.payload
        changes_pending = True
        candidate_configuration["hold"] = new_hold_mode

    elif message.topic == "cmnd/thermostat/temperature":
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
        html = f'''<status version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/status"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><pingRate>0</pingRate><dealerConfigPingRate>0</dealerConfigPingRate><weatherPingRate>14400</weatherPingRate><equipEventsPingRate>0</equipEventsPingRate><historyPingRate>0</historyPingRate><iduFaultsPingRate>0</iduFaultsPingRate><iduStatusPingRate>86400</iduStatusPingRate><oduFaultsPingRate>0</oduFaultsPingRate><oduStatusPingRate>0</oduStatusPingRate><configHasChanges>off</configHasChanges><dealerConfigHasChanges>off</dealerConfigHasChanges><dealerHasChanges>off</dealerHasChanges><oduConfigHasChanges>off</oduConfigHasChanges><iduConfigHasChanges>off</iduConfigHasChanges><utilityEventsHasChanges>off</utilityEventsHasChanges></status>'''
        self.send_response(200)
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Connection", "keep-alive")
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(bytes(html, "utf8"))

    def send_empty_200(self):
        #print("** empty **")
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
            print(f'''New configuration: {candidate_configuration}''')
            html = f'''<config version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/config"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><atom:link rel="http://{api_server_address}/rels/dealer_config" href="http://{api_server_address}/systems/{thermostat_serial}/dealer_config"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><mode>{candidate_configuration["mode"]}</mode><fan>{candidate_configuration["fan"]}</fan><blight>10</blight><timeFormat>12</timeFormat><dst>on</dst><volume>high</volume><soundType>click</soundType><scrLockout>off</scrLockout><scrLockoutCode>0000</scrLockoutCode><humSetpoint>45</humSetpoint><dehumSetpoint>45</dehumSetpoint><utilityEvent/><zones><zone id="1"><name>Zone 1</name><hold>{candidate_configuration["hold"]}</hold><otmr/><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp><program><day id="1"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="2"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="3"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="4"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="5"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="6"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day><day id="7"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="2"><time>08:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period><period id="4"><time>22:00</time><htsp>{candidate_configuration["htsp"]}</htsp><clsp>{candidate_configuration["clsp"]}</clsp></period></day></program></zone></zones></config>'''
            self.send_response(200)
            self.send_header("Content-Length", len(html))
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        else:
            # Send 0 length 200 response
            self.send_empty_200()


    def do_POST(self):
        #print()
        data = self.rfile.read(int(self.headers.get('Content-length'))).decode("utf-8")
        #print("data unparsed: {}".format(data))
        data = unquote(data).strip("data=")
        #print("data parsed: {}".format(data))
        global current_configuration
        global candidate_configuration
        global first_start

        html = ""
        match = False

        monitored = ["rt","rh","mode","fan","coolicon","heaticon","fanicon","hold","filtrlvl","clsp","htsp","opstat","iducfm","oat","oducoiltmp"]
        paths = ["/status", "/odu_status"]
        received_message = {}

        if len(data) >= 45:
            for path in paths:
                if path in self.path:
                    match = True
                    break

            # Parse and create dict of received message for paths we care about
            if match == True:
                try:
                    root = ET.fromstring(data)
                except:
                    if "/status" in self.path:
                        self.send_no_changes()
                    else:
                        self.send_empty_200
                    return

                children = list(root)
                for child in root.iter():
                    received_message[child.tag] = child.text

            # ignore other paths
            else:
                # Send 0 length 200 response
                self.send_empty_200()
                return

            if "/odu_status" in self.path or "/status" in self.path:

                # We don't need any kind of response for this path
                if "/odu_status" in self.path:
                    self.send_empty_200()

                for option in monitored:
                    if option in received_message:
                        current_configuration[option] = received_message[option]

                client.publish(thermostat_state_topic, str(current_configuration).replace("'",'"').replace("None",'""'), retain=True)

                # Initialize candidate_configuration as current_configuration at first start
                if "/status" in self.path and first_start == True:
                    candidate_configuration['clsp'] = current_configuration['clsp']
                    candidate_configuration['htsp'] = current_configuration['htsp']
                    candidate_configuration['mode'] = current_configuration['mode']
                    first_start = False
                    self.send_no_changes()

                elif "/status" in self.path and changes_pending == False:
                    self.send_no_changes()

                elif "/status" in self.path and changes_pending == True:
                    print("Responding with change notice...")
                    html = f'''<status version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/status"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><pingRate>0</pingRate><dealerConfigPingRate>0</dealerConfigPingRate><weatherPingRate>14400</weatherPingRate><equipEventsPingRate>0</equipEventsPingRate><historyPingRate>0</historyPingRate><iduFaultsPingRate>0</iduFaultsPingRate><iduStatusPingRate>86400</iduStatusPingRate><oduFaultsPingRate>0</oduFaultsPingRate><oduStatusPingRate>0</oduStatusPingRate><configHasChanges>on</configHasChanges><dealerConfigHasChanges>off</dealerConfigHasChanges><dealerHasChanges>off</dealerHasChanges><oduConfigHasChanges>off</oduConfigHasChanges><iduConfigHasChanges>off</iduConfigHasChanges><utilityEventsHasChanges>off</utilityEventsHasChanges></status>'''
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(html)))
                    self.send_header("Content-Type", "application/xml; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(bytes(html, "utf8"))


        # Malformed message
        else:
            if "/status" in self.path:
                self.send_no_changes()

            else:
                # Send 0 length 200 response
                self.send_empty_200()

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

client = mqttClient.Client("thermostat_api_server")
server = ThreadingSimpleServer(('0.0.0.0', api_server_listen_port), MyHttpRequestHandler)

client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_address, mqtt_port)

client.loop_start()
client.subscribe(thermostat_command_topic)
server.serve_forever()
