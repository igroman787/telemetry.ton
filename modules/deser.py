import datetime as DateTimeLibrary
from modules.utils import Dict, row2dict
from models import Data

def get_nodes_deser_data(db_session, network_name, limit):
	query = db_session.query(Data.adnl_address,
							Data.datetime,
							Data.unixtime,
							Data.masterchainblock,
							Data.stateserializermasterchainseqno)
	current_time = DateTimeLibrary.datetime.now()
	need_datetime = current_time - DateTimeLibrary.timedelta(minutes=limit)
	query = query.filter(Data.datetime>need_datetime)
	query = query.order_by(Data.datetime.desc())
	print(f"get_nodes_deser_data query: {query}")
	nodes_data = row2dict(query.all())
	return nodes_data
#end define

def calculate_node_deser_data(nodes_data):
	for data in nodes_data:
		if data.masterchainblock:
			data.out_of_ser = data.masterchainblock - data.stateserializermasterchainseqno
		else:
			data.out_of_ser = -1
	return nodes_data
#end define

def sort_nodes_data(nodes_data, nodes_list):
	print("sort_nodes_data:", len(nodes_data), len(nodes_list))
	buff_data = Dict()
	result = list()
	for data in nodes_data:
		if data.adnl_address not in buff_data:
			buff_data[data.adnl_address] = list()
		buff_data[data.adnl_address].append(data)
	for adnl in nodes_list:
		if adnl not in buff_data:
			continue
		buff = list()
		for data in buff_data[adnl]:
			buff.append(data)
		result.append(buff)
	return result
#end define
