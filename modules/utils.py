import time
import json
import base64
import datetime as DateTimeLibrary

class Dict(dict):
	def __init__(self, *args, **kwargs):
		for item in args:
			self._parse_dict(item)
		self._parse_dict(kwargs)
	#end define

	def _parse_dict(self, d):
		for key, value in d.items():
			if type(value) in [dict, Dict]:
				value = Dict(value)
			if type(value) == list:
				value = self._parse_list(value)
			self[key] = value
	#end define

	def _parse_list(self, lst):
		result = list()
		for value in lst:
			if type(value) in [dict, Dict]:
				value = Dict(value)
			result.append(value)
		return result
	#end define

	def __setattr__(self, key, value):
		self[key] = value
	#end define

	def __getattr__(self, key):
		return self.get(key)
	#end define
#end class

def is_hash(input_data):
	try:
		input_bytes = bytes.fromhex(input_data)
		if len(input_bytes) > 6:
			return True
		else:
			return False
	except:
		return False
#end define

def get_hash_type(input_data):
	input_bytes = bytes.fromhex(input_data)
	input_bytes_len = len(input_bytes)
	if input_bytes_len == 20:
		return "git_hash"
	elif input_bytes_len == 32:
		return "key_hash"
	else:
		raise Exception(f"get_hash_type error: input_data type unknown")
#end define

def get_short_git_hash(full_hash):
	if full_hash is None:
		short_hash = None
	elif len(full_hash) > 7:
		short_hash = full_hash[:7]
	else:
		short_hash = full_hash
	return short_hash
#end define

def get_short_hash(full_hash):
	if full_hash is None:
		short_hash = None
	elif len(full_hash) > 12:
		end = len(full_hash)
		short_hash = full_hash[0:6] + "..." + full_hash[end-6:end]
	else:
		short_hash = full_hash
	return short_hash
#end define

def timeago(timestamp=False):
	"""
	Get a datetime object or a int() Epoch timestamp and return a
	pretty string like 'an hour ago', 'Yesterday', '3 months ago',
	'just now', etc
	"""
	now = DateTimeLibrary.datetime.now()
	if type(timestamp) is int:
		diff = now - DateTimeLibrary.datetime.fromtimestamp(timestamp)
	elif isinstance(timestamp, DateTimeLibrary.datetime):
		diff = now - timestamp
	elif timestamp is None:
		return
	second_diff = diff.seconds
	day_diff = diff.days

	if day_diff < 0:
		return ''

	if day_diff == 0:
		if second_diff < 60:
			return "just now"
		if second_diff < 120:
			return "a minute ago"
		if second_diff < 3600:
			return str(second_diff // 60) + " minutes ago"
		if second_diff < 7200:
			return "an hour ago"
		if second_diff < 86400:
			return str(second_diff // 3600) + " hours ago"
	if day_diff < 31:
		return str(day_diff) + " days ago"
	if day_diff < 365:
		return str(day_diff // 30) + " months ago"
	return str(day_diff // 365) + " years ago"
#end define

def get_avg_from_json(json_text):
	if json_text == None:
		return None
	buff = json.loads(json_text)
	avg_buff = 0
	for key, value in buff.items():
		if value != None:
			avg_buff += value
	result = avg_buff / len(buff)
	return round(result, 2)
#end define

def get_max_from_json(json_text):
	if json_text == None:
		return None
	buff = json.loads(json_text)
	result = 0
	for key, value in buff.items():
		if value != None and value > result:
			result = value
	return result
#end define

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

def row2dict(row):
	if row == None:
		return
	elif type(row) == list:
		result = list()
		for item in row:
			result.append(row2dict(item))
	else:
		result = Dict()
		result.update(row._mapping)
	return result
#end define

def get_working_time(func, *args, **kwargs):
	start = time.time()
	result = func(*args, **kwargs)
	diff = time.time() - start
	if diff > 1:
		print(f"{func.__name__} take: {diff} seconds")
	return result
#end define