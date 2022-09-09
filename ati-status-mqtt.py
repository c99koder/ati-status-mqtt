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

import glob, sqlite3, json, time, sys, os, platform
from datetime import datetime
import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

backups = {}

if platform.system() == "Windows":
	ACRONIS_SCRIPTS_PATH = "C:\\ProgramData\\Acronis\\TrueImageHome\\Scripts\\"
	ACRONIS_DB_PATH = "C:\\ProgramData\\Acronis\\TrueImageHome\\Database\\"

	if sys.executable.endswith("pythonw.exe"):
		sys.stdout = open(os.path.join(os.getenv("TEMP"), "stdout-"+os.path.basename(sys.argv[0]))+".log", "w");
		sys.stderr = open(os.path.join(os.getenv("TEMP"), "stderr-"+os.path.basename(sys.argv[0]))+".log", "w")
elif platform.system() == "Darwin":
	ACRONIS_SCRIPTS_PATH = "/Library/Application Support/Acronis/TrueImageHome/Scripts/"
	ACRONIS_DB_PATH = "/Library/Application Support/Acronis/TrueImageHome/Database/"
else:
	ACRONIS_SCRIPTS_PATH = "/tmp/ati/"
	ACRONIS_DB_PATH = "/tmp/ati/"

# Load backup names from XML scripts
for script in glob.glob(ACRONIS_SCRIPTS_PATH + "*.tib.tis"):
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

	backup['icon'] = 'mdi:folder-question'
	backups[uuid] = backup

if len(backups) == 0:
	print("No Acronis True Image backups found")
	sys.exit(1)

# Load status notifications from SQLite database
if platform.system() == "Windows":
	os.system("copy " + ACRONIS_DB_PATH + "TrayCenterStorage* " + os.getenv("TEMP") + " > NUL")
	db = sqlite3.connect(os.getenv("TEMP") + "\\TrayCenterStorage")
else:
	db = sqlite3.connect(ACRONIS_DB_PATH + "TrayCenterStorage")
db.row_factory = sqlite3.Row
cursor = db.cursor()
for row in cursor.execute("select * from Notification_ where event_ = 'backup_finished' order by date_ asc"):
	if row['userDataTaskGuid_'] in backups:
		backup = backups[row['userDataTaskGuid_']]
		backup['timestamp'] = datetime.fromtimestamp(int(row['date_'])).isoformat()
		backup['state'] = row['status_']
		backup['text'] = row['text_']
		if backup['state'] == "success":
			backup['icon'] = 'mdi:folder-check'
		else:
		 	backup['icon'] = 'mdi:folder-alert'

db.close()
if platform.system() == "Windows":
	os.system("del " + os.getenv("TEMP") + "\\TrayCenterStorage* > NUL")

print("Publishing sensor configuration to MQTT")
client = mqtt.Client()
client.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
client.connect(MQTT_HOST, MQTT_PORT)

for uuid, backup in backups.items():
	client.publish("homeassistant/sensor/" + uuid + "/config", 
		json.dumps({'name': 'Acronis ' + backup['friendly_name'],
			'unique_id': uuid,
			'icon': backup['icon'],
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
