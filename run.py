import os, json, base64
from waitress import serve
from web import app, local_settings, settings_filepath


def bytes_to_base64(data):
	base64_bytes = base64.b64encode(data)
	base64_text = base64_bytes.decode("utf-8")
	return base64_text
#end define

def base64_to_bytes(base64_text):
	text_bytes = base64_text.encode("utf-8")
	data = base64.b64decode(text_bytes)
	return data
#end define

def read_settings():
	global local_settings
	if not os.path.isfile(settings_filepath):
		return
	file = open(settings_filepath)
	data = file.read()
	file.close()
	local_settings.update(json.loads(data))
#end define

def write_settings():
	global local_settings
	file = open(settings_filepath, 'w')
	data = json.dumps(local_settings, indent=4)
	file.write(data)
	file.close()
#end define

def init():
	global local_settings
	read_settings()

	if "secret_key_b64" not in local_settings:
			secret_key = os.urandom(256)
			local_settings["secret_key_b64"] = bytes_to_base64(secret_key)
	if "admin_keys" not in local_settings:
			admin_keys = list()
			new_admin_key = bytes_to_base64(os.urandom(512))
			admin_keys.append(new_admin_key)
			local_settings["admin_keys"] = admin_keys
			print(f"new_admin_key: {new_admin_key}")
	if "mysql" not in local_settings:
			mysql = dict()
			mysql["user"] = input("write DB user: ")
			mysql["passwd"] = input("write DB passwd: ")
			mysql["db"] = input("write DB name: ")
			mysql["host"] = "127.0.0.1"
			local_settings["mysql"] = mysql
	write_settings()

	secret_key_b64 = local_settings.get("secret_key_b64")
	app.secret_key = base64_to_bytes(secret_key_b64)
	serve(app, host='0.0.0.0', port=8000)
#end define

init()
