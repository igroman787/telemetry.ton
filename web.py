import os
import json
import base64
import datetime as DateTimeLibrary
from flask import Flask, url_for, render_template, session, request, redirect, abort, Markup, send_from_directory
from werkzeug.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Data, Validator



settings = dict()
app = Flask(__name__)
settings_filepath = "settings.json"
default_table_columns = [ "ctrl", "notes", "adnl_address", "datetime", "remote_country", "stake", "cpu", "memory", "net_load", "db_usage", "mytonctrl_hash", "validator_hash", "out_of_sync", "validator_pubkey", "network_name" ]
all_table_columns = default_table_columns + ["pps", "disks_load_avg", "disks_load_avg_percent", "iops_avg", "disks_load_max", "disks_load_max_percent", "iops_max", "swap_total", "swap_usage", "validator_efficiency", "validator_wallet_address"]



class Dict(dict):
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			self[key] = value
		self.to_class()
	#end define
	
	def to_class(self):
		for key, value in self.items():
			setattr(self, key, value)
		#end for
	#end define
	
	def to_dict(self):
		for key, value in self.items():
			self[key] = getattr(self, key)
		#end for
#end class

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = DateTimeLibrary.timedelta(days=730)
#end define

@app.route('/favicon.ico')
def favicon():
	return send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico", mimetype="image/vnd.microsoft.icon")
#end define

@app.route('/')
def index():
	user_key = session.get("user_key")
	return render_template("index.html", user_key=user_key, redirect_url=request.path)
#end define

@app.route("/login", methods=["POST"])
def login():
	session["user_key"] = request.form.get("user_key")
	redirect_url = request.form.get("redirect_url")
	return redirect(redirect_url)
#end define

@app.route("/logoute", methods=["POST"])
def logoute():
	session["user_key"] = None
	redirect_url = request.form.get("redirect_url")
	return redirect(redirect_url)
#end define

@app.route("/new_admin", methods=["POST"])
def new_admin():
	user_key = session.get("user_key")
	if is_admin(user_key) == False:
		abort(401)
	#end if
	
	redirect_url = request.form.get("redirect_url")
	new_admin_key = request.form.get("new_admin_key")
	if len(new_admin_key) < 256:
		abort(412)
	#end if
	
	admin_keys = settings.get("admin_keys")
	admin_keys.append(new_admin_key)
	write_settings()
	return redirect(redirect_url)
#end define

@app.route("/admin")
def admin():
	user_key = session.get("user_key")
	if is_admin(user_key) == False:
		abort(401)
	#end if
	
	admin_keys = settings.get("admin_keys")
	admin_keys_len = len(admin_keys)
	return render_template("admin.html", admin_keys_len=admin_keys_len, redirect_url=request.path)
#end define

@app.route("/settings")
def settings():
	select = Dict()
	select["items"] = all_table_columns
	select["size"] = len(all_table_columns)
	select["multiple"] = True
	select.to_class()
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
	db_engine, db_session = create_db_connect()
	adnls_data = get_adnls_list(db_session)

	table_name = f"Result {len(adnls_data)} nodes"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_lines = create_table_lines(db_session, user_table_columns, adnls_data)
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Nodes list", table_name=table_name, table_lines=table_lines)
#end define

@app.route("/node")
def node():
	adnl = request.args.get("adnl", type=str)
	limit = request.args.get("limit", type=int, default=1000)
	if is_user_access() == False:
		abort(401)
	#end if
	
	db_engine, db_session = create_db_connect()
	node_data = get_node_data_from_db(db_session, adnl, limit)
	node_data = calculate_node_data(node_data)

	table_name = f"Result for {adnl}"
	user_table_columns = session.get("user_table_columns", default_table_columns)
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
	if is_user_access() == False:
		abort(401)
	#end if
	
	nodes_data = list()
	max_cpu_load = 0
	max_memory_usage = 0
	db_engine, db_session = create_db_connect()
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

@app.route("/validators")
def validators():
	network_name = request.args.get("network_name", default="mainnet", type=str)
	
	db_engine, db_session = create_db_connect()
	validators_data = get_validators_data(db_session, network_name)
	
	
	table_name = f"Result {len(validators_data)} validators, start_work_time={validators_data[0].start_work_time}, end_work_time={validators_data[0].end_work_time}, network_name={validators_data[0].network_name}"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_columns = user_table_columns + ["weight"]
	table_lines = create_table_lines(db_session, table_columns, validators_data)
	
	close_db_connect(db_engine, db_session)
	return render_template("nodes.html", title_text="Validators list", table_name=table_name, table_lines=table_lines)
#end define

@app.route("/favorites")
def favorites():
	db_engine, db_session = create_db_connect()
	favorites_list = get_favorites_list()
	
	table_name = f"Result {len(favorites_list)} favorites"
	user_table_columns = session.get("user_table_columns", default_table_columns)
	table_lines = create_table_lines(db_session, user_table_columns, favorites_list)
	
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
	
	db_engine, db_session = create_db_connect()
	adnls_data = get_adnls_list(db_session)
	nodes_data = get_nodes_data(db_session)
	
	table_lines = list()
	table_header = ["ctrl", "notes", "adnl_address", "validator_pubkey", "network_name", "warning_text"]
	table_lines.append(table_header)
	for data in adnls_data:
		node_data = get_node_data(db_session, nodes_data, data.adnl_address, ignore_user_access=True)
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

def set_favorites_list(favorites_list):
	session["favorites_list"] = favorites_list
#end define

def get_favorites_list(return_adnls_list=False):
	favorites_list_buff = session.get("favorites_list", list())
	favorites_list = list()
	for item in favorites_list_buff:
		buff = Dict()
		buff.update(item)
		buff.to_class()
		favorites_list.append(buff)
	#end for
	
	if return_adnls_list == False:
		return favorites_list
	#end if
	
	favorites_list_buff = favorites_list
	favorites_list = list()
	for item in favorites_list_buff:
		favorites_list.append(item.adnl_address)
	return favorites_list
#end define

def create_star_button(adnl_address):
	star_button = Dict()
	favorites_list = get_favorites_list(return_adnls_list=True)
	if adnl_address in favorites_list:
		star_button["active"] = True
		star_button["url"] = f"/del_favorite"
	else:
		star_button["active"] = False
		star_button["url"] = f"/add_favorite"
	star_button.to_class()
	return star_button
#end define

def get_note(adnl_address):
	notes = session.get("notes", dict())
	note = notes.get(adnl_address, "")
	return note
#end define

def get_warning(node_data):
	critical = False
	warnings = list()
	if node_data.disks_load_avg_percent != None and node_data.disks_load_avg_percent > 85:
		warnings.append("disks_load > 85%")
	if node_data.db_usage != None and node_data.db_usage > 95:
		warnings.append("db_usage > 95%")
		critical = True
	elif node_data.db_usage != None and node_data.db_usage > 85:
		warnings.append("db_usage > 85%")
	if node_data.net_load != None and node_data.net_load > 200:
		warnings.append("net_load > 200 Mbit/s")
	if node_data.out_of_sync != None and node_data.out_of_sync > 3600:
		warnings.append("out_of_sync > 3600 seconds")
		critical = True
	elif node_data.out_of_sync != None and node_data.out_of_sync > 60:
		warnings.append("out_of_sync > 60 seconds")
	#end if
	
	warning = None
	if len(warnings) > 0:
		warning = Dict()
		warning["text"] = ", ".join(warnings)
		warning["critical"] = critical
		warning.to_class()
	return warning
#end define

def create_html_ctrl(adnl_address, node_data):
	ctrl = Dict()
	ctrl["adnl_address"] = adnl_address
	ctrl["short_adnl_address"] = get_short_hash(adnl_address)
	ctrl["redirect_url"] = request.path
	ctrl["star_button"] = create_star_button(adnl_address)
	ctrl["note"] = get_note(adnl_address)
	ctrl["warning"] = get_warning(node_data)
	ctrl.to_class()
	html_ctrl = Markup(render_template("ctrl.html", ctrl=ctrl))
	return html_ctrl
#end define

def create_html_chart(title, nodes_data, max=None):
	chart_datasets = list()
	for node_data in nodes_data:
		short_adnl = get_short_hash(node_data[0].adnl_address)
		dataset = Dict()
		dataset["label"] = short_adnl
		chart_data = list()
		for data in node_data:
			time_m = data.unixtime * 1000
			chart_data.append([time_m, data.get(title)])
		#end for
		dataset["data"] = chart_data
		dataset["borderWidth"] = 0.7
		dataset["pointRadius"] = 0
		dataset["pointHitRadius"] = 30
		dataset["tension"] = 0.1
		chart_datasets.append(dataset)
	#end for
	
	chart = Dict()
	chart["id"] = os.urandom(4).hex()
	chart["title"] = title
	chart["datasets"] = chart_datasets
	chart["max"] = max
	html_chart = Markup(render_template("chart.html", chart=chart))
	return html_chart
#end define

def create_table_lines_for_node(table_columns, input_data):
	table_lines = list()
	table_header = list()
	for column in table_columns:
		table_header.append(column)
	table_lines.append(table_header)
	
	for node_data in input_data:
		table_line = list()
		for column in table_columns:
			if column == "datetime":
				datetime = DateTimeLibrary.datetime.fromtimestamp(node_data.unixtime).strftime("%d.%m.%Y, %H:%M:%S")
				table_line.append(datetime)
			elif column == "cpu":
				cpu_load = f"{node_data.cpu_load}".rjust(5)
				cpu_number = f"/{node_data.cpu_number}".rjust(4)
				cpu = f"{cpu_load} {cpu_number}"
				table_line.append(cpu)
			elif column == "memory":
				memory_usage = f"{node_data.memory_usage}".rjust(6)
				memory_total = f"/{node_data.memory_total}".rjust(7)
				memory = f"{memory_usage} {memory_total} Gb"
				table_line.append(memory)
			elif column == "net_load":
				net_load = f"{node_data.net_load} Mbit/s".rjust(13)
				table_line.append(net_load)
			elif column == "db_usage":
				db_usage = f"{node_data.db_usage} %".rjust(7)
				table_line.append(db_usage)
			elif column == "disks_load_avg":
				disks_load_avg = f"{node_data.disks_load_avg} Mb/s".rjust(11)
				table_line.append(disks_load_avg)
			elif column == "disks_load_avg_percent":
				disks_load_avg_percent = f"{node_data.disks_load_avg_percent} %".rjust(7)
				table_line.append(disks_load_avg_percent)
			elif column in input_data:
				column_data = input_data.get(column)
				if is_hash(column_data):
					hash_type = get_hash_type(column_data)
					if hash_type == "git_hash":
						column_data = get_short_git_hash(column_data)
					elif hash_type == "key_hash":
						column_data = get_short_hash(column_data)
				table_line.append(column_data)
			elif column in node_data:
				column_data = node_data.get(column)
				if is_hash(column_data):
					hash_type = get_hash_type(column_data)
					if hash_type == "git_hash":
						column_data = get_short_git_hash(column_data)
					elif hash_type == "key_hash":
						column_data = get_short_hash(column_data)
				table_line.append(column_data)
			#else:
			#	raise Exception(f"create_table_lines error: `{column}` not found in input_data and node_data")
		table_lines.append(table_line)
	return table_lines
#end define

def create_table_lines(db_session, table_columns, input_data):
	table_lines = list()
	table_header = list()
	for column in table_columns:
		table_header.append(column)
	table_lines.append(table_header)
	
	nodes_data = get_nodes_data(db_session)
	for data in input_data:
		table_line = list()
		node_data = get_node_data(db_session, nodes_data, data.adnl_address)
		node_data = calculate_node_data(node_data)
		for column in table_columns:
			if column == "ctrl":
				html_ctrl = create_html_ctrl(data.adnl_address, node_data)
				table_line.append(html_ctrl)
			elif column == "notes":
				note = get_note(data.adnl_address)
				table_line.append(note)
			elif column == "datetime":
				datetime = timeago(node_data.unixtime)
				table_line.append(datetime)
			elif column == "cpu":
				cpu_load = f"{node_data.cpu_load}".rjust(5)
				cpu_number = f"/{node_data.cpu_number}".rjust(4)
				cpu = f"{cpu_load} {cpu_number}"
				table_line.append(cpu)
			elif column == "memory":
				memory_usage = f"{node_data.memory_usage}".rjust(6)
				memory_total = f"/{node_data.memory_total}".rjust(7)
				memory = f"{memory_usage} {memory_total} Gb"
				table_line.append(memory)
			elif column == "net_load":
				net_load = f"{node_data.net_load} Mbit/s".rjust(13)
				table_line.append(net_load)
			elif column == "db_usage":
				db_usage = f"{node_data.db_usage} %".rjust(7)
				table_line.append(db_usage)
			elif column == "disks_load_avg":
				disks_load_avg = f"{node_data.disks_load_avg} Mb/s".rjust(11)
				table_line.append(disks_load_avg)
			elif column == "disks_load_avg_percent":
				disks_load_avg_percent = f"{node_data.disks_load_avg_percent} %".rjust(7)
				table_line.append(disks_load_avg_percent)
			elif column in data:
				column_data = data.get(column)
				if is_hash(column_data):
					hash_type = get_hash_type(column_data)
					if hash_type == "git_hash":
						column_data = get_short_git_hash(column_data)
					elif hash_type == "key_hash":
						column_data = get_short_hash(column_data)
				table_line.append(column_data)
			elif column in node_data:
				column_data = node_data.get(column)
				if is_hash(column_data):
					hash_type = get_hash_type(column_data)
					if hash_type == "git_hash":
						column_data = get_short_git_hash(column_data)
					elif hash_type == "key_hash":
						column_data = get_short_hash(column_data)
				table_line.append(column_data)
			#else:
			#	raise Exception(f"create_table_lines error: `{column}` not found in input_data and node_data")
		table_lines.append(table_line)
	return table_lines
#end define

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

@app.errorhandler(HTTPException)
def handle_exception(error):
	title_text = f"{error.code} {error.name}"
	return render_template("error_page.html", title_text=title_text, error_code=error.code, error_name=error.name, error_description=error.description), error.code
#end define

def get_adnls_list(db_session):
	query = db_session.query(Data.adnl_address)
	query = query.group_by(Data.adnl_address)
	adnls_data = query.all()
	return row2dict(adnls_data)
#end define

def get_last_election_id(db_session, network_name):
	query = db_session.query(Validator.start_work_time)
	query = db_session.query(Validator)
	query = query.filter_by(network_name=network_name)
	query = query.order_by(Validator.id.desc())
	data = query.first()
	election_id = data.start_work_time
	return election_id
#end define

def get_validators_data(db_session, network_name):
	election_id = get_last_election_id(db_session, network_name)
	query = db_session.query(Validator.adnl_address, 
							Validator.datetime, 
							Validator.start_work_time, 
							Validator.end_work_time, 
							Validator.validator_pubkey, 
							Validator.weight, 
							Validator.network_name)
	query = query.filter_by(network_name=network_name, start_work_time=election_id)
	query = query.group_by(Validator.adnl_address)
	validators_data = query.all()
	return row2dict(validators_data)
#end define

def get_nodes_data(db_session):
	current_time = DateTimeLibrary.datetime.now()
	need_datetime = current_time - DateTimeLibrary.timedelta(minutes=10)
	query = db_session.query(Data.adnl_address, 
							Data.datetime, 
							Data.remote_country, 
							Data.remote_isp, 
							Data.stake, 
							Data.tps, 
							Data.cpu_load, 
							Data.cpu_number, 
							Data.memory_usage, 
							Data.memory_total, 
							Data.swap_total, 
							Data.swap_usage, 
							Data.net_load, 
							Data.pps, 
							Data.disks_load, 
							Data.disks_load_percent, 
							Data.iops, 
							Data.db_usage, 
							Data.mytonctrl_hash, 
							Data.validator_hash, 
							Data.out_of_sync, 
							Data.unixtime, 
							Data.validator_pubkey, 
							Data.validator_efficiency,
							Data.validator_wallet_address,
							Data.network_name)
	query = query.filter(Data.datetime>need_datetime)
	query = query.order_by(Data.datetime.desc())
	nodes_data = query.all()
	return row2dict(nodes_data)
#end define

def get_node_data(db_session, data, search_adnl_address, ignore_user_access=False):
	empty_node_data = create_empty_node_data()
	if ignore_user_access == False and is_user_access() == False:
		return empty_node_data
	for node_data in data:
		if node_data.adnl_address == search_adnl_address:
			return node_data
	node_data = get_node_data_from_db(db_session, search_adnl_address)
	if node_data is None:
		return empty_node_data
	return node_data
#end define

def calculate_node_data(node_data):
	if type(node_data) == list:
		result = list()
		for item in node_data:
			result.append(calculate_node_data(item))
		return result
	#end if
	
	iops_avg = get_avg_from_json(node_data.iops)
	iops_max = get_max_from_json(node_data.iops)
	disks_load_avg = get_avg_from_json(node_data.disks_load)
	disks_load_max = get_max_from_json(node_data.disks_load)
	disks_load_avg_percent = get_avg_from_json(node_data.disks_load_percent)
	disks_load_max_percent = get_max_from_json(node_data.disks_load_percent)
	
	node_data["iops_avg"] = iops_avg
	node_data["iops_max"] = iops_max
	node_data["disks_load_avg"] = disks_load_avg
	node_data["disks_load_max"] = disks_load_max
	node_data["disks_load_avg_percent"] = disks_load_avg_percent
	node_data["disks_load_max_percent"] = disks_load_max_percent
	node_data.to_class()
	return node_data
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

def create_empty_node_data():
	data = Dict()
	data["adnl_address"] = None
	data["datetime"] = None
	data["remote_country"] = None
	data["stake"] = None
	data["cpu_load"] = None
	data["cpu_number"] = None
	data["memory_usage"] = None
	data["memory_total"] = None
	data["net_load"] = None
	data["db_usage"] = None
	data["mytonctrl_hash"] = None
	data["validator_hash"] = None
	data["unixtime"] = None
	data["out_of_sync"] = None
	data["validator_pubkey"] = None
	data["network_name"] = None
	data["pps"] = None
	data["validator_efficiency"] = None
	data["validator_wallet_address"] = None
	data["swap_total"] = None
	data["swap_usage"] = None
	data["iops"] = None
	data["disks_load"] = None
	data["disks_load_percent"] = None
	data.to_class()
	return data
#end define

def is_user_access(node_key=None):
	user_key = session.get("user_key")
	if is_admin(user_key):
		return True
	if node_key != None and user_key == node_key:
		return True
	return False
#end define

def is_admin(user_key):
	admin_keys = settings.get("admin_keys")
	if user_key in admin_keys:
		return True
	return False
#end define

def get_node_data_from_db(db_session, adnl_address, limit=1):
	query = db_session.query(Data.adnl_address, 
							Data.datetime, 
							Data.remote_country, 
							Data.remote_isp, 
							Data.stake, 
							Data.tps, 
							Data.cpu_load, 
							Data.cpu_number, 
							Data.memory_usage, 
							Data.memory_total, 
							Data.swap_total, 
							Data.swap_usage, 
							Data.net_load, 
							Data.pps, 
							Data.disks_load, 
							Data.disks_load_percent, 
							Data.iops, 
							Data.db_usage, 
							Data.mytonctrl_hash, 
							Data.validator_hash, 
							Data.out_of_sync, 
							Data.unixtime, 
							Data.validator_pubkey, 
							Data.validator_efficiency,
							Data.validator_wallet_address,
							Data.network_name)
	query = query.filter_by(adnl_address=adnl_address)
	query = query.order_by(Data.id.desc())
	if limit == 1:
		data = query.first()
	else:
		query = query.limit(limit)
		data = query.all()
	return row2dict(data)
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
		result.to_class()
	return result
#end define

def create_db_connect():
	global settings
	# Create memory connect
	mysql = settings.get("mysql")
	user = mysql.get("user")
	passwd = mysql.get("passwd")
	host = mysql.get("host")
	db = mysql.get("db")
	mysqlConnectUrl = f"mysql://{user}:{passwd}@{host}/{db}"
	db_engine = create_engine(mysqlConnectUrl, echo=False)
	db_session_function = sessionmaker(bind=db_engine)
	db_session = db_session_function()
	return db_engine, db_session
#end define

def close_db_connect(db_engine, db_session):
	db_session.commit()
	db_session.close()
	db_engine.dispose()
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

def if_request_arg_true(s):
	return s.lower() == "true"
#end define

def read_settings():
	global settings
	if not os.path.isfile(settings_filepath):
		return
	file = open(settings_filepath)
	data = file.read()
	file.close()
	settings = json.loads(data)
#end define

def write_settings():
	global settings
	file = open(settings_filepath, 'w')
	data = json.dumps(settings, indent=4)
	file.write(data)
	file.close()
#end define

def init():
	global settings
	read_settings()
	
	if "secret_key_b64" not in settings:
		secret_key = os.urandom(256)
		settings["secret_key_b64"] = bytes_to_base64(secret_key)
	if "admin_keys" not in settings:
		admin_keys = list()
		new_admin_key = bytes_to_base64(os.urandom(512))
		admin_keys.append(new_admin_key)
		settings["admin_keys"] = admin_keys
		print(f"new_admin_key: {new_admin_key}")
	if "mysql" not in settings:
		mysql = dict()
		mysql["user"] = input("write DB user: ")
		mysql["passwd"] = input("write DB passwd: ")
		mysql["db"] = input("write DB name: ")
		mysql["host"] = "127.0.0.1"
		settings["mysql"] = mysql
	write_settings()
	
	secret_key_b64 = settings.get("secret_key_b64")
	app.secret_key = base64_to_bytes(secret_key_b64)
	
	app.logger.info("start web server")
	app.run(host="127.0.0.1", port=8000)
#end define

if __name__ == "__main__":
	init()
#end define
