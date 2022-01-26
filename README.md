# Thermostat MQTT container
<a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a><br>

Acts as API server for Observer Communicating HVAC controller (TSTAT0201CW). Bridges MQTT and thermostat for control through applications such as Home Assistant. You'll need to point your thermostat at this application by modifying the observer server address on the thermostat.

## Usage

### Example docker-compose

```yaml
version: '3.2'
services:
    thermostat_api_server:
        container_name: thermostat_api_server
        image: ghcr.io/aneisch/thermostat_api_server_docker:latest
        ports:
            - '8080:8080'
        environment:
            # Name for Device in HA
            - THERMOSTAT_NAME=Upstairs
            - THERMOSTAT_SERIAL=5687J272316
            - MQTT_SERVER=10.0.1.22
            # Used in reply to thermostat
            - API_SERVER_ADDRESS=10.0.1.22 
        restart: always
```
### Home Assistant Configuration

Uses [MQTT Discovery](https://www.home-assistant.io/docs/mqtt/discovery/) to add climate device and associated sensors. If MQTT discovery is enabled, no configuration should be necessary aside from setting container environment variables.  

![Home Assistant Entities](entities.png)
