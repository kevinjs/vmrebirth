#!/bin/bash

if [ $# -lt 6 ]
then 
	echo "Usage:    auto_launch username password source_host source_file_path dest_directory dest_image_name"
	echo "Example:  auto_launch cnic cnic_passwd 192.168.136.73 /home/cnic/centos.img /tmp/images/ my_centos.img"
	exit 0
fi

SRC_USER=$1
SRC_PASSWD=$2
SRC_HOST=$3
SRC_FILE=$4
DST_DIR=$5
DST_IMAGE_NAME=$6


#copy source image to storage of Openstack
scp $SRC_USER@$SRC_HOST:$SRC_FILE $DST_DIR$DST_FILE
echo "=================================================="
echo "SCP opeartion finished..."
echo "=================================================="
echo 
echo 

exit 0

#upload the image to Dashboard
#create user, add role, add tenant.
keystone='keystone --os_tenant_name admin --os_username admin --os_password csdb123cnic --os_auth_url http://192.168.136.79:5000/v2.0'
#TENANT_ID=$(keystone tenant-list | awk '/[^_]admin/{print $2}')
keystone --os_tenant_name admin --os_username admin --os_password csdb123cnic --os_auth_url http://192.168.136.79:5000/v2.0 tenant-create --name $SRC_USER --description $SRC_USER
TENANT_ID=$($keystone tenant-list | awk "/`echo $SRC_USER`/" | awk '{print $2}')
echo "Tenant ID is `echo $TENANT_ID`\n"
$keystone user-create --name $SRC_USER --tenant-id $TENANT_ID --pass $SRC_PASSWD --email $SRC_USER@example.com --enabled true
USER_ID=$($keystone user-list | awk "/`echo $SRC_USER`/" | awk '{print $2}')
ROLE_ID=$($keystone role-list | awk '/Member/{print $2}')
$keystone user-role-add --user-id $USER_ID --role-id $ROLE_ID --tenant-id $TENANT_ID
echo "=================================================="
echo "User create, Role add finished..."
printf "TENANT_ID is `echo $TENANT_ID`\n"
printf "USER_ID is `echo $USER_ID`\n"
printf "ROLE_ID is `echo $ROLE_ID`\n"
echo "=================================================="
echo 
echo 


#call Glance API to upload image
TOKEN=$($keystone --os_tenant_name cnic --os_username cnic --os_password cnic --os_auth_url http://192.168.136.79:5000/v2.0 token-get | grep id |grep -v '_'|awk '{print $4}')
GLANCE_HOSTPORT="192.168.136.79:9292"
#alias glance=glance --os-auth-token $TOKEN --os-image-url http://192.168.136.79:9292
glance --os-auth-token $TOKEN --os-image-url http://192.168.136.79:9292 image-create --name "$DST_IMAGE_NAME" --container-format=bare --disk-format qcow2 < $DST_DIR$DST_IMAGE_NAME
SRC_IMAGE_ID=$(glance --os-auth-token $TOKEN --os-image-url http://192.168.136.79:9292 image-list |grep $DST_IMAGE_NAME |awk '{print $2}')
ADMIN_TENANT_ID=$($keystone tenant-list | awk '/[^_]admin/{print $2}')
glance --os-auth-token $TOKEN --os-image-url http://192.168.136.79:9292 member-add $SRC_IMAGE_ID $ADMIN_TENANT_ID 
echo "=================================================="
echo "Image create finished..."
echo "=================================================="
echo 
echo 


#launch the image uploaded 
#nova keypair-add test > test.pem
#chmod 600 test.pem
nova --os_username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.136.79:5000/v2.0 boot --image $DST_IMAGE_NAME --flavor m1.tiny --key_name test myAnotherServer
echo "=================================================="
echo "Image launch finished..."
echo "=================================================="
echo  
echo 

#stop the source image
