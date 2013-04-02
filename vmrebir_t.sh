#!/bin/sh

alias nova='nova --os_username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.22:5000/v2.0'
alias swift='export OS_TENANT_NAME=admin;swift -v -V 2.0 -A http://192.168.138.22:5000/v2.0 -U admin -K csdb123cnic'

cserv='192.168.138.22'
dbu='root'
dbp='csdb123cnic'


#srcserv=$1
#echo 'src_server: '$srcserv
dstserv=$2
echo 'dst_server: '$dstserv
vm=$1

#step1: List all vm in src server
#tarvm=`nova-manage vm list | grep $srcserv | awk '{print $1}'`

#for vm in $tarvm
#do
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
echo 's5 done!'
	
#step6:
instance_mac=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep mac | awk -F'"' '{print $2}'`
echo $instance_mac
instance_ip=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep IP | awk -F'"' '{print $4}'`
echo $instance_ip

#step7:
echo -e "\n$instance_mac,$hostname.novalocal,$instance_ip" >> /opt/stack/data/nova/networks/nova-br100.conf
echo 's7 done!'

#step8:
/etc/init.d/libvirt-bin restart
echo 's8 done!'

#step9:
cd /opt/stack/data/nova/instances/$instance_name/
chown stack:stack *
chmod 777 *

virsh define libvirt.xml
virsh start $instance_name

echo 'rebirth vm done!'
	
#done
