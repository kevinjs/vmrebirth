#export OS_TENANT_NAME=admin
#export OS_USERNAME=admin
#export OS_PASSWORD=csdb123cnic
#export OS_AUTH_URL="http://192.168.138.32:5000/v2.0"

alias nova='nova --os_username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0'
alias swift='export OS_TENANT_NAME=admin;swift -v -V 2.0 -A http://192.168.138.32:5000/v2.0 -U admin -K csdb123cnic'
