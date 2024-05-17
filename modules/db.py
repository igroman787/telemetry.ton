from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Data, Validator
from modules.utils import Dict, row2dict

def create_db_connect(local_settings):
	# Create memory connect
	mysql = local_settings.get("mysql")
	user = mysql.get("user")
	passwd = mysql.get("passwd")
	host = mysql.get("host")
	db = mysql.get("db")
	mysqlConnectUrl = f"mysql://{user}:{passwd}@{host}/{db}"
	connect_args = {"connect_timeout": 10}
	db_engine = create_engine(mysqlConnectUrl, echo=False, connect_args=connect_args)
	db_session_function = sessionmaker(bind=db_engine)
	db_session = db_session_function()
	return db_engine, db_session
#end define

def close_db_connect(db_engine, db_session):
	db_session.commit()
	db_session.close()
	db_engine.dispose()
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

def get_validators_list(db_session, network_name):
	election_id = get_last_election_id(db_session, network_name)
	query = db_session.query(Validator.adnl_address)
	query = query.filter_by(network_name=network_name, start_work_time=election_id)
	query = query.group_by(Validator.adnl_address)
	validators_list = list()
	for row in query.all():
		validators_list.append(row.adnl_address)
	return validators_list
#end define
