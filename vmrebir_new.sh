#!/bin/sh

alias nova='nova --os_username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0'
alias swift='export OS_TENANT_NAME=admin;swift -v -V 2.0 -A http://192.168.138.32:5000/v2.0 -U admin -K csdb123cnic'

mysql_h='192.168.138.32'
mysql_u='root'
mysql_p='csdb123cnic'

vm=$1
dstserv=$2

hostname=`mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "select hostname from instances where uuid = '$vm';" nova | awk '{print $1}'`

echo 'Move '$hostname'('$vm') to '$dstserv

#Step1:
echo 'Step1 >>'
mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "update instances set host='$dstserv' where uuid = '$vm'; select row_count();" nova | awk '{print $1}'

#Step2:
echo 'Step2 >>'
instance_name=`nova show $vm | grep instance_name | awk '{print $4}'`
echo 'instance_name: '$instance_name

#Step3:
echo 'Step3 >>'
cd /opt/stack/data/nova/instances/$instance_name
filter_name=`cat libvirt.xml | grep filter= | awk -F'"' '{print $2}'`
echo 'filter_name: '$filter_name

#step4:
echo 'Step4 >>'
#filter_uuid=`uuidgen $filter_name`
#echo 'filter_uuid: '$filter_uuid
#cat > /etc/libvirt/nwfilter/$filter_name.xml << _done_
#<filter name='$filter_name' chain='root'>
#<uuid>$filter_uuid</uuid>
#<filterref filter='nova-base'/>
#</filter>
#_done_

if [ -f "/etc/libvirt/nwfilter/$filter_name.xml" ]; then
echo 'Filter file has existed'
else
#echo 'Not Exist'
echo 'filter_uuid: '$filter_uuid
cat > /etc/libvirt/nwfilter/$filter_name.xml << _done_
<filter name='$filter_name' chain='root'>
<uuid>$filter_uuid</uuid>
<filterref filter='nova-base'/>
</filter>
_done_
fi


#step5:
echo 'Step5 >>' 
instance_mac=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep mac | awk -F'"' '{print $2}'`
echo 'MAC: '$instance_mac
instance_ip=`cat /opt/stack/data/nova/instances/$instance_name/libvirt.xml | grep IP | awk -F'"' '{print $4}'`
echo 'IP: '$instance_ip
echo -e "\n$instance_mac,$hostname.novalocal,$instance_ip" >> /opt/stack/data/nova/networks/nova-br100.conf

#step6:
echo 'Step6 >>'
#/etc/init.d/libvirt-bin restart
#service libvirt-bin restart
lv_pid=`service libvirt-bin restart | grep process | awk '{print $4}'`
echo $lv_pid > /opt/stack/data/nova/networks/nova-br100.pid

#step7:
echo 'Step7 >>'
cd /opt/stack/data/nova/instances/$instance_name/
chown stack:stack *
chmod 777 *

virsh define libvirt.xml
virsh start $instance_name

fixed_id=`mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "select id from fixed_ips where address='$instance_ip';" nova | awk '{print $1}'`
echo $fixed_id

if [ ! $fixed_id = "" ]; then
        #echo $fixed_id
        float_ip=`mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "select address from floating_ips where fixed_ip_id='$fixed_id';" nova | awk '{print $1}'`
	echo $float_ip
        if [ ! $float_ip = "" ]; then
                #echo $float_ip
		mysql -h$mysql_h -u$mysql_u -p$mysql_p -N -e "update floating_ips set host = '$dstserv' where fixed_ip_id='$fixed_id'; select row_count();" nova
		
		#step8:
		echo 'Step8 >>'
		ip addr add $float_ip/32 dev br100
		
		iptables -t nat -A nova-network-OUTPUT -d $float_ip/32 -j DNAT --to-destination $instance_ip
		iptables -t nat -A nova-network-PREROUTING -d $float_ip/32 -j DNAT --to-destination $instance_ip
		iptables -t nat -A nova-network-float-snat -s $instance_ip/32 -j SNAT --to-source $float_ip
#		iptables-save > /etc/iptables.up.rules
		sysctl -p
        fi
else
echo "None floating_ips"
fi

echo 'Done!'
