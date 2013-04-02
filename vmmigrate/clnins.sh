#!/bin/sh

tarins=$1

tarid=`mysql -uroot -pcsdb123cnic -N -e "select id from instances where display_name='$tarins';" nova | awk '{print $1}'`

echo $tarid

mysql -uroot -pcsdb123cnic -N -e "update instances set deleted_at = updated_at, deleted = 1, power_state = 0, vm_state= 'deleted', terminated_at = updated_at, task_state = NULL where id = $tarid; select row_count();" nova

mysql -uroot -pcsdb123cnic -N -e "update instance_info_caches set deleted_at = updated_at, deleted = 1 where id = $tarid; select row_count();" nova
