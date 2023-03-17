#!/usr/bin/env python3
# -*- coding: utf_8 -*-

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, INT, BIGINT, FLOAT, DateTime, Boolean


# SQLAlchemy init
Base = declarative_base()

class Validator(Base):
	__tablename__ = "validators"
	id = Column(BIGINT, primary_key=True)
	datetime = Column(DateTime, index=True)
	adnl_address = Column(String(64), index=True)
	validator_pubkey = Column(String(64), index=True)
	validator_weight = Column(BIGINT)
	start_work_time = Column(BIGINT, index=True)
	end_work_time = Column(BIGINT, index=True)
	total_weight = Column(BIGINT)
	weight = Column(FLOAT)
	network_name = Column(String(8), index=True)
#end class

class Data(Base):
	__tablename__ = "data"
	id = Column(BIGINT, primary_key=True)
	datetime = Column(DateTime, index=True)
	adnl_address = Column(String(64), index=True)
	remote_country = Column(String(16), index=True)
	remote_isp = Column(String(64), index=True)
	
	cpu_number = Column(INT, index=True)
	db_usage = Column(FLOAT, index=True)
	stake = Column(INT, index=True)
	
	tps = Column(FLOAT)
	cpu_load = Column(FLOAT, index=True)
	net_load = Column(FLOAT, index=True)
	pps = Column(FLOAT, index=True)
	
	disks_load = Column(String(1024))
	disks_load_percent = Column(String(1024))
	iops = Column(String(1024))
	
	mytonctrl_hash = Column(String(40), index=True)
	validator_hash = Column(String(40), index=True)
	
	memory_total = Column(FLOAT, index=True)
	memory_usage = Column(FLOAT, index=True)
	
	swap_total = Column(FLOAT, index=True)
	swap_usage = Column(FLOAT, index=True)
	
	uname_machine = Column(String(64))
	uname_release = Column(String(64))
	uname_sysname = Column(String(64))
	uname_version = Column(String(64))
	
	vprocess_cpu_percent = Column(BIGINT)
	vprocess_memory_data = Column(BIGINT)
	vprocess_memory_dirty = Column(BIGINT)
	vprocess_memory_lib = Column(BIGINT)
	vprocess_memory_rss = Column(BIGINT)
	vprocess_memory_shared = Column(BIGINT)
	vprocess_memory_text = Column(BIGINT)
	vprocess_memory_vms = Column(BIGINT)
	
	unixtime = Column(BIGINT)
	is_working = Column(Boolean)
	out_of_sync = Column(BIGINT)
	masterchainblock = Column(BIGINT)
	masterchainblocktime = Column(BIGINT)
	gcmasterchainblock = Column(BIGINT)
	keymasterchainblock = Column(BIGINT)
	rotatemasterchainblock = Column(BIGINT)
	shardclientmasterchainseqno = Column(BIGINT)
	stateserializermasterchainseqno = Column(BIGINT)
	
	validator_pubkey = Column(String(64))
	validator_weight = Column(BIGINT)
	validator_mr = Column(FLOAT)
	validator_wr = Column(FLOAT)
	validator_efficiency = Column(FLOAT, index=True)
	validator_wallet_address = Column(String(64), index=True)
	
	network_name = Column(String(8), index=True)
#end class
