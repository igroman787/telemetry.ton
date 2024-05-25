import datetime as DateTimeLibrary
from modules.utils import Dict, is_hash, get_hash_type, get_short_git_hash, get_short_hash, timeago, get_avg_from_json, get_max_from_json, bytes_to_base64, base64_to_bytes, row2dict
from modules.is_s import is_user_access, is_admin, if_request_arg_true
from models import Data, Validator

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
	return node_data
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
	return data
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
							Data.network_name,
							Data.masterchainblock,
							Data.stateserializermasterchainseqno)
	query = query.filter_by(adnl_address=adnl_address)
	query = query.order_by(Data.id.desc())
	if limit == 1:
		data = query.first()
	else:
		query = query.limit(limit)
		data = query.all()
	return row2dict(data)
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
