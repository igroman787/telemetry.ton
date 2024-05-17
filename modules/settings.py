import os
import json

def read_settings(local_settings):
	if not os.path.isfile(settings_filepath):
		return
	file = open(settings_filepath)
	data = file.read()
	file.close()
	local_settings = json.loads(data)
#end define

def write_settings(local_settings):
	file = open(settings_filepath, 'w')
	data = json.dumps(local_settings, indent=4)
	file.write(data)
	file.close()
#end define
