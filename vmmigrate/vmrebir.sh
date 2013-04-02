#!/bin/sh

cserv='192.168.138.22'
dbu='root'
dbp='csdb123cnic'


srcserv=$1
echo 'src_server: '$srcserv
dstserv=$2
echo 'dst_server: '$dstserv

#step1: List all vm in src server
tarvm=`nova-manage vm list | grep $srcserv | awk '{print $1}'`

for vm in $tarvm
do
	#for each virtual machine do
	echo 'Virtual Machine: '$vm
	dispname=$vm
	hostname=${dispname}
	#hostname=${dispname//_/-}

	#step2:
	echo -n 'Update instances: '
	mysql -h$cserv -u$dbu -p$dbp -N -e "update instances set host='$dstserv' where display_name = '$hostname'; select row_count();" nova | awk '{print $1}'
	
	#step3:
	instance_name=`nova show $hostname | grep instance_name | awk '{print $4}'`
	echo 'instance_name: '$instance_name
	
	#step4:
	cd /opt/stack/data/nova/instances/$instance_name
	filter_name=`cat libvirt.xml | grep filter= | awk -F'"' '{print $2}'`
	echo 'filter_name: '$filter_name
	
	#step5:
	filter_uuid=`uuidgen $filter_name`
	echo 'filter_uuid: '$filter_uuid
	cat > /etc/libvirt/nwfilter//$filter_name.xml << _done_
<filter name='$filter_name' chain='root'>
<uuid>$filter_uuid</uuid>
<filterref filter='nova-base'/>
</filter>
_done_
	
	#step6:
	instance_mac=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep mac | awk -F'"' '{print $2}'`
	instance_ip=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep IP | awk -F'"' '{print $4}'`

	#step7:
	echo -e "\n$instance_mac,$hostname.novalocal,$instance_ip" >> /opt/stack/data/nova/networks/nova-br100.conf

	#step8:
	/etc/init.d/libvirt-bin restart

	#step9:
	cd /opt/stack/data/nova/instances/$instance_name/
	chown stack:stack *
	chmod 777 *
	virsh define libvirt.xml
	virsh start $instance_name
	
done

#echo $tarvm
#echo ${#tarvm}
