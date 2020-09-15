#!/usr/bin/env python3

import http.server
import socketserver
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqttClient
import datetime
import os

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

# Some default messages
thermostat_message = {}
new_configuration = {"mode":"cool", "fan": "auto", "htsp":"65", "clsp":"80"}
changes_pending = False

api_server_address = os.environ['API_SERVER_ADDRESS']
api_server_listen_port = int(os.environ['API_SERVER_LISTEN_PORT'])
mqtt_address = os.environ['MQTT_SERVER']
mqtt_port = int(os.environ['MQTT_PORT'])
thermostat_command_topic = os.environ['THERMOSTAT_COMMAND_TOPIC']
thermostat_state_topic = os.environ['THERMOSTAT_STATE_TOPIC']
thermostat_serial = os.environ['THERMOSTAT_SERIAL']

client = mqttClient.Client("thermostat_api_server")
client.connect(mqtt_address, mqtt_port)

def on_message(client, userdata, message):
    global changes_pending
    global thermostat_message
    global new_configuration
    message.payload = message.payload.decode("utf-8") 

    if message.topic == "cmnd/thermostat/operating_mode":
        new_operating_mode = message.payload

    elif message.topic == "cmnd/thermostat/fan_mode":
        new_fan_mode = message.payload

    elif message.topic == "cmnd/thermostat/hold":
        new_hold_mode = message.payload

    elif message.topic == "cmnd/thermostat/temperature":
        new_temperature = message.payload

        if 'clsp' in thermostat_message:
            if thermostat_message['mode'] == "cool" and new_temperature != thermostat_message['clsp']:
                changes_pending = True
                new_configuration["clsp"] = new_temperature.split(".")[0]

        if 'htsp' in thermostat_message:
            if thermostat_message['mode'] == "heat" and new_temperature != thermostat_message['htsp']:
                changes_pending = True
                new_configuration["htsp"] = new_temperature.split(".")[0]

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global changes_pending
        global thermostat_message
        global new_configuration
        html = ""

        self.send_response(200)

        if "/Alive" in self.path:
            html = "alive"
            self.send_header("Content-Length", "5")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        if "/time" in self.path:
            html = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.send_header("Content-Length", len(html))
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        if "/config" in self.path:
            print("Sending new config...")
            html = f'''<config version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/config"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><atom:link rel="http://{api_server_address}/rels/dealer_config" href="http://{api_server_address}/systems/{thermostat_serial}/dealer_config"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><mode>auto</mode><fan>auto</fan><blight>40</blight><timeFormat>12</timeFormat><dst>on</dst><volume>high</volume><soundType>click</soundType><scrLockout>off</scrLockout><scrLockoutCode>0000</scrLockoutCode><humSetpoint>45</humSetpoint><dehumSetpoint>45</dehumSetpoint><utilityEvent/><zones><zone id="1"><name>Zone 1</name><hold>on</hold><otmr/><htsp>{new_configuration["htsp"]}</htsp><clsp>{new_configuration["clsp"]}</clsp><program><day id="1"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="2"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="3"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="4"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="5"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="6"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day><day id="7"><period id="1"><time>06:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="2"><time>08:00</time><htsp>70</htsp><clsp>78</clsp></period><period id="3"><time>17:00</time><htsp>71</htsp><clsp>78</clsp></period><period id="4"><time>22:00</time><htsp>70</htsp><clsp>78</clsp></period></day></program></zone></zones></config>'''
            self.send_header("Content-Length", len(html))
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        return

    def do_POST(self):
        length = int(self.headers.get('Content-length', 0))
        data = self.rfile.read(length).decode()
        html = ""
        global changes_pending
        global thermostat_message
        global new_configuration

        paths = ["/status", "/notifications"]

        if length != 0:
            for path in paths:
                if path in self.path:
                    data = unquote(data).strip("data=")
                    root = ET.fromstring(data)
                    children = root.getchildren()
                    for child in root.iter():
                       thermostat_message[child.tag] = child.text
                    client.publish(thermostat_state_topic, str(thermostat_message).replace("'",'"').replace("None",'""'), retain=True)


        if changes_pending == True and "/status" in self.path:
            print("Responding with change notice...")
            changes_pending = False
            html = f'''<status version="1.9" xmlns:atom="http://www.w3.org/2005/Atom"><atom:link rel="self" href="http://{api_server_address}/systems/{thermostat_serial}/status"/><atom:link rel="http://{api_server_address}/rels/system" href="http://{api_server_address}/systems/{thermostat_serial}"/><timestamp>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</timestamp><pingRate>0</pingRate><dealerConfigPingRate>0</dealerConfigPingRate><weatherPingRate>14400</weatherPingRate><equipEventsPingRate>0</equipEventsPingRate><historyPingRate>0</historyPingRate><iduFaultsPingRate>0</iduFaultsPingRate><iduStatusPingRate>86400</iduStatusPingRate><oduFaultsPingRate>0</oduFaultsPingRate><oduStatusPingRate>0</oduStatusPingRate><configHasChanges>on</configHasChanges><dealerConfigHasChanges>off</dealerConfigHasChanges><dealerHasChanges>off</dealerHasChanges><oduConfigHasChanges>off</oduConfigHasChanges><iduConfigHasChanges>off</iduConfigHasChanges><utilityEventsHasChanges>off</utilityEventsHasChanges></status>'''
            self.send_response(200)
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))

        else:
            # Send 0 length 200 response
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        return


handler_object = MyHttpRequestHandler
my_server = socketserver.TCPServer(("", api_server_listen_port), handler_object)
client.on_message = on_message
client.loop_start()
client.subscribe(thermostat_command_topic)
my_server.serve_forever()
