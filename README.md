# ATI-Status-MQTT
Publish Acronis True Image backup status notifications to Home Assistant via MQTT

## Configuration
Open `ati-status-mqtt.py` and enter your MQTT hostname and credentials into the variables at the top of the file

## Usage
**Note:** This script currently only supports Acronis True Image 2021

Check your Python version and make sure version 3.8 or newer is installed on your system:
```sh
python3 --version
```

Install required python3 modules:
```sh
pip3 install paho-mqtt
```

Running the Python script will publish the status of all your backups using the notifications that are currently available in the Acronis status menu extra applet.  Home Assistant will automatically discover the new entities, and you can customize the names / icons as usual.

## Installation

### Mac
Install LaunchAgent to run the script hourly (optional):
```sh
sudo cp ati-status-mqtt.py /usr/local/bin
mkdir -p ~/Library/LaunchAgents
cp org.c99.ati-status-mqtt.plist ~/Library/LaunchAgents
launchctl load -w ~/Library/LaunchAgents/org.c99.ati-status-mqtt.plist
```

### Windows
Create a new task in Windows Task Scheduler:
 * Copy `ati-status-mqtt.py` to `C:\ati-status-mqtt.pyw` *(The pyw extension prevents a CMD window from opening when the script runs)*
 * Launch `Windows Task Scheduler`
 * Right click `Task Scheduler Library` and choose `Import Task…`
 * Browse to `ATI-Status-MQTT.xml`
 * Customize settings and then save the task
 * Right click the task and choose `Run` to start it

## Example Lovelace Card
Below is a sample card for the Lovelace dashboard using [Auto-Entities](https://github.com/thomasloven/lovelace-auto-entities) and [Template-Entity-Row](https://github.com/thomasloven/lovelace-template-entity-row)

![Lovelace Screenshot](https://raw.githubusercontent.com/c99koder/ati-status-mqtt/main/screenshots/card.png)

```yaml
type: custom:auto-entities
card:
  type: entities
  title: Acronis Backup Status
filter:
  include:
    - entity_id: sensor.acronis_*
      options:
        type: custom:template-entity-row
        state: ''
        icon: >-
          {% if is_state(config.entity, 'success') %}hass:check-circle{% else
          %}hass:alert-circle{%endif%}
        secondary: '{{ state_attr(config.entity, ''text'') }}'
        color: >-
          {% if is_state(config.entity, 'success') %}lightgreen{% else
          %}tomato{%endif%}
        active: true
```

## License

Copyright (C) 2021 Sam Steele. Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
