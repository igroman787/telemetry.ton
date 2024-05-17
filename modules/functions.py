import os
from flask import Flask, url_for, render_template, session, request, redirect, abort, Markup, send_from_directory
from modules.utils import Dict, is_hash, get_hash_type, get_short_git_hash, get_short_hash, timeago, get_avg_from_json, get_max_from_json, bytes_to_base64, base64_to_bytes, row2dict
from modules.nodes import get_nodes_data, get_node_data, calculate_node_data, create_empty_node_data, get_node_data_from_db, get_validators_data

def set_favorites_list(favorites_list):
	session["favorites_list"] = favorites_list
#end define

def get_favorites_list(return_adnls_list=False):
	favorites_list_buff = session.get("favorites_list", list())
	favorites_list = list()
	for item in favorites_list_buff:
		buff = Dict()
		buff.update(item)
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
