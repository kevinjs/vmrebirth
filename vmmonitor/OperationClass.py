#!/usr/bin/env python
'''
Created on Mar 27, 2013

@author: jingshao@cnic.cn
'''

from RunCommandClass import RunCommand

class Operation:
#    def __init__(self):
    
    '''
    Reboot VM instance by uuid
    '''
    def reboot_ins(self, ins_uuid):
        rc = RunCommand()
        ins_name = rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 show " + ins_uuid + " | grep OS-EXT-SRV-ATTR:instance_name | awk '{print $4}'").strip()
    
        if ins_name != None and ins_name != '':
            rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 reboot " + ins_uuid )
        return '<OPERATION: REBOOT>'
    
    def migrate_ins(self, ins_uuid, target_host):
        return '<OPERATION: MIGRATE>'
    
