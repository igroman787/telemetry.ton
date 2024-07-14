from flask import Flask, url_for, render_template, session, request, redirect, abort, send_from_directory

def is_user_access(local_settings, node_key=None):
	#user_key = session.get("user_key")
	user_key = request.cookies.get("user_key")
	print(f"is_user_access -> user_key: {user_key}, cookies: {request.cookies}")
	if is_admin(local_settings, user_key):
		return True
	if node_key != None and user_key == node_key:
		return True
	return False
#end define

def is_admin(local_settings, user_key):
	admin_keys = local_settings.get("admin_keys")
	if user_key in admin_keys:
		return True
	return False
#end define

def if_request_arg_true(s):
	return s.lower() == "true"
#end define
