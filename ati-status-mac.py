#!/usr/bin/env python3

#  Copyright (C) 2021 Sam Steele
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import glob, sqlite3, json, time
from datetime import datetime
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt

MQTT_HOST = "homeassistant.local"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

backups = {}

# Load backup names from XML scripts
for script in glob.glob("/Library/Application Support/Acronis/TrueImageHome/Scripts/*.tib.tis"):
	root = ET.parse(script).getroot()
	uuid = root.findall("uuid")[0].text
	backup = {'friendly_name': root.findall("display")[0].text}
	backup_node = None
	if root.findall("stage/operations/online_backup"):
		backup_node = "stage/operations/online_backup"
		backup['type'] = "Cloud"
	elif root.findall("stage/operations/replicate"):
		continue
	elif root.findall("stage/operations/backup"):
		backup_node = "stage/operations/backup"
		backup['type'] = "Local"
	elif root.findall("stage/operations/hybrid_backup"):
		backup_node = "stage/operations/hybrid_backup"
		backup['type'] = "Hybrid"
	else:
		print("Unknown backup type for UUID " + uuid)
		continue

	if root.findall(backup_node + "/disk_source"):
		backup['source'] = "Disk"
	if root.findall(backup_node + "/files"):
		backup['source'] = "Folder"

	for volume in root.findall(backup_node + "/archive_options/volumes_locations/volume_location"):
		if not 'volumes' in backup:
			backup['volumes'] = []
		uri = volume.get("uri")
		if not uri in backup['volumes']:
			backup['volumes'].append(uri)
	backups[uuid] = backup

if len(backups) == 0:
	print("No Acronis True Image backups found")
	sys.exit(1)

# Load status notifications from SQLite database
db = sqlite3.connect("/Library/Application Support/Acronis/TrueImageHome/Database/TrayCenterStorage")
db.row_factory = sqlite3.Row
cursor = db.cursor()
for row in cursor.execute("select * from Notification_ where event_ = 'backup_finished' order by date_ asc"):
	if row['userDataTaskGuid_'] in backups:
		backup = backups[row['userDataTaskGuid_']]
		backup['timestamp'] = datetime.fromtimestamp(int(row['date_'])).isoformat()
		backup['state'] = row['status_']
		backup['text'] = row['text_']

db.close()

print("Publishing sensor configuration to MQTT")
client = mqtt.Client()
client.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
client.connect(MQTT_HOST, MQTT_PORT)

for uuid, backup in backups.items():
	client.publish("homeassistant/sensor/" + uuid + "/config", 
		json.dumps({'name': 'Acronis ' + backup['friendly_name'],
			'state_topic': "homeassistant/sensor/" + uuid + "/state",
			'json_attributes_topic': "homeassistant/sensor/" + uuid + "/attributes",
			'availability_mode': 'latest',
			'availability_topic': "homeassistant/sensor/" + uuid + "/available"
			}), retain=True)

print("Publishing states to MQTT")
for uuid, backup in backups.items():
	if 'timestamp' in backup:
		print(backup['timestamp'] + " " + backup['friendly_name'] + " - " + backup['state'] + ": " + backup['text'])
		client.publish("homeassistant/sensor/" + uuid + "/state", backup['state'], retain=True)
		client.publish("homeassistant/sensor/" + uuid + "/attributes", json.dumps(backup), retain=True)
		client.publish("homeassistant/sensor/" + uuid + "/available", 'online', retain=True)
	else:
		print("No status available for " + backup['friendly_name'])
		client.publish("homeassistant/sensor/" + uuid + "/available", 'offline', retain=True)

client.disconnect()
