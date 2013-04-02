#!/bin/bash

mysql_h='192.168.138.32'
mysql_u='root'
mysql_p='csdb123cnic'

target_ins=$1

if [ ! $target_ins == "" ]; then
	echo 'instance_uuid: '$target_ins

	mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "update instances set deleted_at = updated_at, deleted = 1, power_state = 0, vm_state= 'deleted', terminated_at = updated_at, task_state = NULL where uuid = '$target_ins'; select row_count();" nova
	mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "update instance_info_caches set deleted_at = updated_at, deleted = 1 where instance_uuid = '$target_ins'; select row_count();" nova
	proc_info=`ps -ef |grep kvm |grep $target_ins | grep -v grep | awk '{print $2}'`
#	echo $proc_info
	if [ ! $proc_info == "" ]; then
		#target_PID=echo $proc_info | awk '{print $2}'
#		echo $proc_info
		kill $proc_info
		echo 'Clean '$proc_info' done!'
	else
		echo 'Clean done!'
	fi 
else
	echo 'Useage: ./cleanins.sh instance_uuid'
fi
