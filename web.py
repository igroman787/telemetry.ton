import os
import json
import base64
import datetime as DateTimeLibrary
from flask import Flask, url_for, render_template, request, redirect, abort, send_from_directory, make_response #session
from werkzeug.exceptions import HTTPException


from models import Base, Data, Validator
from modules.utils import Dict, is_hash, get_hash_type, get_short_git_hash, get_short_hash, timeago, get_avg_from_json, get_max_from_json, bytes_to_base64, base64_to_bytes, row2dict, get_working_time
from modules.nodes import get_nodes_data, get_node_data, calculate_node_data, create_empty_node_data, get_node_data_from_db, get_validators_data
from modules.db import create_db_connect, close_db_connect, get_adnls_list, get_last_election_id, get_validators_list
from modules.functions import set_favorites_list, get_favorites_list, create_star_button, get_note, get_warning, create_html_ctrl, create_html_chart, create_table_lines_for_node, create_table_lines
from modules.deser import get_nodes_deser_data, calculate_node_deser_data, sort_nodes_data
from modules.is_s import is_user_access, is_admin, if_request_arg_true


local_settings = Dict()
app = Flask(__name__)
settings_filepath = "settings.json"

default_table_columns = [ "ctrl", "notes", "adnl_address", "datetime", "remote_country", "stake", "cpu", "memory", "net_load", "db_usage", "mytonctrl_hash", "validator_hash", "out_of_sync", "validator_pubkey", "network_name" ]
all_table_columns = default_table_columns + ["pps", "disks_load_avg", "disks_load_avg_percent", "iops_avg", "disks_load_max", "disks_load_max_percent", "iops_max", "swap_total", "swap_usage", "validator_efficiency", "validator_wallet_address"]


#@app.before_request
#def make_session_permanent():
#    session.permanent = True
#    app.permanent_session_lifetime = DateTimeLibrary.timedelta(days=730)
#end define

@app.route('/favicon.ico')
def favicon():
	static_dir = os.path.join(app.root_path, "static")
	return send_from_directory(static_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon")
#end define

@app.route('/')
def index():
	#user_key = session.get("user_key")
	user_key = request.cookies.get("user_key")
	print(f"index -> user_key: {user_key}, cookies: {request.cookies}")
	rend = render_template("index.html", user_key=user_key, redirect_url=request.path)
	resp = make_response(rend)
	return resp
#end define

@app.route("/login", methods=["POST"])
def login():
	user_key = request.form.get("user_key")
	redirect_url = request.form.get("redirect_url")
	print(f"login -> user_key: {user_key}, redirect_url: {redirect_url}, cookies: {request.cookies}")
	#session["user_key"] = user_key
	rend = redirect(redirect_url)
	resp = make_response(rend)
	resp.set_cookie("user_key", user_key)
	return resp
#end define

@app.route("/logoute", methods=["POST"])
def logoute():
	#session["user_key"] = None
	redirect_url = request.form.get("redirect_url")
	print(f"logoute -> redirect_url: {redirect_url}, cookies: {request.cookies}")
	rend = redirect(redirect_url)
	resp = make_response(rend)
	resp.set_cookie("user_key", "", expires=0)
	return resp
#end define

@app.route("/new_admin", methods=["POST"])
def new_admin():
	user_key = session.get("user_key")
	if is_admin(local_settings, user_key) == False:
		abort(401)
	#end if
	
	redirect_url = request.form.get("redirect_url")
	new_admin_key = request.form.get("new_admin_key")
	if len(new_admin_key) < 256:
		abort(412)
	#end if
	
	admin_keys = local_settings.get("admin_keys")
	admin_keys.append(new_admin_key)
	write_settings()
	return redirect(redirect_url)
#end define

@app.route("/admin")
def admin():
	user_key = session.get("user_key")
	if is_admin(local_settings, user_key) == False:
		abort(401)
	#end if
	
	admin_keys = local_settings.get("admin_keys")
	admin_keys_len = len(admin_keys)
	return render_template("admin.html", admin_keys_len=admin_keys_len, redirect_url=request.path)
#end define

@app.route("/settings")
def settings():
	select = Dict()
	select["items"] = all_table_columns
	select["size"] = len(all_table_columns)
	select["multiple"] = True
	return render_template("settings.html", select=select, redirect_url=request.path)
#end define

@app.route("/add_settings", methods=["POST"])
def add_settings():
	redirect_url = request.form.get("redirect_url")
	select_items = request.form.getlist("select_items")
	session["user_table_columns"] = select_items
	return redirect(redirect_url)
#end define

@app.route("/nodes")
def nodes():
	db_engine, db_session = create_db_connect(local_settings)
	adnls_data = get_adnls_list(db_session)

	table_name = f"Result {len(adnls_data)} nodes"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_lines = create_table_lines(local_settings, db_session, user_table_columns, adnls_data)
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Nodes list", table_name=table_name, table_lines=table_lines)
#end define

@app.route("/node")
def node():
	adnl = request.args.get("adnl", type=str)
	limit = request.args.get("limit", type=int, default=1000)
	if is_user_access(local_settings) == False:
		abort(401)
	#end if
	
	db_engine, db_session = create_db_connect(local_settings)
	node_data = get_node_data_from_db(db_session, adnl, limit)
	node_data = calculate_node_data(node_data)

	table_name = f"Result for {adnl}"
	user_table_columns = session.get("user_table_columns", default_table_columns).copy()
	for item in ["ctrl", "notes"]:
		if item in user_table_columns:
			user_table_columns.remove(item)
	#end for
	table_lines = create_table_lines_for_node(user_table_columns, node_data)
	
	close_db_connect(db_engine, db_session)
	return render_template("node.html", title_text=table_name, table_name=table_name, table_lines=table_lines)
#end define

@app.route("/charts")
def charts():
	adnls = request.args.get("adnls", type=str)
	limit = request.args.get("limit", type=int, default=1000)
	if is_user_access(local_settings) == False:
		abort(401)
	#end if
	
	nodes_data = list()
	max_cpu_load = 0
	max_memory_usage = 0
	db_engine, db_session = create_db_connect(local_settings)
	adnls = adnls.split(',')
	for adnl in adnls:
		node_data = get_node_data_from_db(db_session, adnl, limit)
		node_data = calculate_node_data(node_data)
		nodes_data.append(node_data)
		if node_data[0].cpu_number > max_cpu_load:
			max_cpu_load = node_data[0].cpu_number
		if node_data[0].memory_total > max_memory_usage:
			max_memory_usage = node_data[0].memory_total
	#end for
	close_db_connect(db_engine, db_session)
	
	out_of_sync_chart = create_html_chart("out_of_sync", nodes_data, 100)
	out_of_ser_chart = create_html_chart("out_of_ser", nodes_data)
	cpu_chart = create_html_chart("cpu_load", nodes_data, max_cpu_load)
	memory_chart = create_html_chart("memory_usage", nodes_data, max_memory_usage)
	net_chart = create_html_chart("net_load", nodes_data, 500)
	disk_chart = create_html_chart("disks_load_max", nodes_data, 250)
	disk_percent_chart = create_html_chart("disks_load_max_percent", nodes_data, 100)
	
	
	charts = list()
	charts.append(out_of_sync_chart)
	charts.append(cpu_chart)
	charts.append(memory_chart)
	charts.append(net_chart)
	charts.append(disk_chart)
	charts.append(disk_percent_chart)
	
	
	return render_template("charts.html", charts=charts)
#end define

@app.route("/deserialization")
def deserialization():
	network_name = request.args.get("network_name", default="mainnet", type=str)
	limit = request.args.get("limit", type=int, default=1440)
	
	nodes_data = list()
	db_engine, db_session = create_db_connect(local_settings)
	#validators_list = get_validators_list(db_session, network_name)
	#nodes_data = get_nodes_deser_data(db_session, network_name, limit)
	#nodes_data = calculate_node_deser_data(nodes_data)
	#validators_data = sort_nodes_data(nodes_data, validators_list)
	validators_list = get_working_time(get_validators_list, db_session, network_name)
	nodes_data = get_working_time(get_nodes_deser_data, db_session, network_name, limit)
	nodes_data = get_working_time(calculate_node_deser_data, nodes_data)
	validators_data = get_working_time(sort_nodes_data, nodes_data, validators_list)
	close_db_connect(db_engine, db_session)

	out_of_ser_chart = create_html_chart("out_of_ser", validators_data, 10**5)
	print(f"print deserialization chart - done")
	return render_template("charts.html", charts=[out_of_ser_chart])
#end define

@app.route("/validators")
def validators():
	network_name = request.args.get("network_name", default="mainnet", type=str)
	
	db_engine, db_session = create_db_connect(local_settings)
	validators_data = get_validators_data(db_session, network_name)
	
	
	table_name = f"Result {len(validators_data)} validators, start_work_time={validators_data[0].start_work_time}, end_work_time={validators_data[0].end_work_time}, network_name={validators_data[0].network_name}"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_columns = user_table_columns + ["weight"]
	table_lines = create_table_lines(local_settings, db_session, table_columns, validators_data)
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Validators list", table_name=table_name, table_lines=table_lines)
#end define

@app.route("/favorites")
def favorites():
	db_engine, db_session = create_db_connect(local_settings)
	favorites_list = get_favorites_list()
	
	table_name = f"Result {len(favorites_list)} favorites"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_lines = create_table_lines(local_settings, db_session, user_table_columns, favorites_list)
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Favorites list", table_name=table_name, table_lines=table_lines)
#end define

@app.route("/add_favorite", methods=["POST"])
def add_favorite():
	adnl_address = request.form.get("adnl_address")
	redirect_url = request.form.get("redirect_url")
	favorites_list = get_favorites_list()
	favorites_list.append(Dict(adnl_address=adnl_address))
	set_favorites_list(favorites_list)
	return redirect(redirect_url)
#end define

@app.route("/del_favorite", methods=["POST"])
def del_favorite():
	adnl_address = request.form.get("adnl_address")
	redirect_url = request.form.get("redirect_url")
	favorites_list = get_favorites_list()
	favorites_list.remove(Dict(adnl_address=adnl_address))
	set_favorites_list(favorites_list)
	return redirect(redirect_url)
#end define

@app.route("/edit_note", methods=["POST"])
def edit_note():
	adnl_address = request.form.get("adnl_address")
	redirect_url = request.form.get("redirect_url")
	notes = session.get("notes", dict())
	notes[adnl_address] = request.form.get("note")
	session["notes"] = notes
	return redirect(redirect_url)
#end define

@app.route("/warnings")
def warnings():
	network_name = request.args.get("network_name", type=str)
	validator = request.args.get("validator", type=if_request_arg_true)
	
	db_engine, db_session = create_db_connect(local_settings)
	adnls_data = get_adnls_list(db_session)
	nodes_data = get_nodes_data(db_session)
	
	table_lines = list()
	table_header = ["ctrl", "notes", "adnl_address", "validator_pubkey", "network_name", "warning_text"]
	table_lines.append(table_header)
	for data in adnls_data:
		node_data = get_node_data(local_settings, db_session, nodes_data, data.adnl_address, ignore_user_access=True)
		node_data = calculate_node_data(node_data)
		if network_name != None and network_name != node_data.network_name:
			continue
		if validator != None and validator != (node_data.validator_pubkey != None):
			continue
		short_adnl_address = get_short_hash(data.adnl_address)
		short_validator_pubkey = get_short_hash(node_data.validator_pubkey)
		html_ctrl = create_html_ctrl(data.adnl_address, node_data)
		note = get_note(data.adnl_address)
		warning = get_warning(node_data)
		if warning != None:
			table_lines.append([html_ctrl, note, short_adnl_address, short_validator_pubkey, node_data.network_name, warning.text])
	#end for
	table_name = f"Result {len(table_lines)-1} warnings"
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Warnings list", table_name=table_name, table_lines=table_lines)
#end define

@app.errorhandler(HTTPException)
def handle_exception(error):
	title_text = f"{error.code} {error.name}"
	return render_template("error_page.html", title_text=title_text, error_code=error.code, error_name=error.name, error_description=error.description), error.code
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
	
	#if "secret_key_b64" not in local_settings:
	#	secret_key = os.urandom(256)
	#	local_settings["secret_key_b64"] = bytes_to_base64(secret_key)
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
	
	#secret_key_b64 = local_settings.get("secret_key_b64")
	#app.secret_key = base64_to_bytes(secret_key_b64)
	
	app.logger.info("start web server")
	app.run(host="0.0.0.0", port=8000, debug=True)
#end define

if __name__ == "__main__":
	init()
#end define
