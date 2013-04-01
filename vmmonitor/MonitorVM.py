#!/usr/bin/env python
'''
Author: jingshao@cnic.cn
    VM monitor service
    - USAGE: VmMonitor.py start/stop/restart
'''

import sys, time, datetime
import json, MySQLdb, redis

from DaemonClass import Daemon
from RunCommandClass import RunCommand
from OperationClass import Operation

'''
Append file
'''
def appendFile(content, filename):
    if len(content) != 0:
        output = open(filename, 'a')
        output.write(content)
        output.close()
    else:
        return

class TestDaemon(Daemon):
    
    def __init__(self, 
                 pidfile, 
                 stdin='/dev/stdin', 
                 stdout='/dev/stdout', 
                 stderr='/dev/stderr',  
                 intvl=10, 
                 wait=5, 
                 reboot=10,
		 logfile='/tmp/test.log'):
        
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.intvl = intvl
        self.wait = wait
        self.reboot = reboot
        self.logfile = logfile
        
    def chk_ins(self, chk_timestamp):
        rc = RunCommand()
        tmp = rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 list ")
        tmps = tmp.strip().split('\n')
        id_list = {}
        
        redis_c = redis.Redis(host='127.0.0.1', port=6379)
    
        for line in tmps:
            if not line.startswith('+'):
                line_s = line.strip().split('|')
                if line_s[1].strip() != 'ID':
                    tmp_dict = {}
    
                    tmp_dict['ins_name'] = line_s[2].strip()
                    tmp_dict['ins_status'] = line_s[3].strip()
    #                tmp_dict['ins_hostname'] = rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 show " + tmp_dict['ins_uuid'] + " | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}'").strip()
                    tmp_dict['chk_time'] = chk_timestamp #check timestamp
                    
                    # select from redis db
                    ins_stat_str = redis_c.lindex(line_s[1].strip(), -1)
                    
                    if ins_stat_str != None and ins_stat_str != '':
                        # "0.590$938392$2097152$vnet2:14844296$vnet2:106438$hda:681078784$hda:531002368$1364366831"
                        ins_stat = ins_stat_str.split('$')
                        
                        tmp_dict['cpu_usage'] = ins_stat[0]
                        tmp_dict['mem_free'] = ins_stat[1]
                        tmp_dict['mem_max'] = ins_stat[2]
                        tmp_dict['nic_in'] = ins_stat[3]
                        tmp_dict['nic_out'] = ins_stat[4]
                        tmp_dict['disk_read'] = ins_stat[5]
                        tmp_dict['disk_write'] = ins_stat[6]
                        
                        tmp_dict['monitor_time'] = ins_stat[len(ins_stat) - 1]
                    else:
                        tmp_dict['monitor_time'] = -1 # Error: no record in redis
                    tmp_dict['repeat_num'] = 0
                    
                    id_list[line_s[1].strip()] = tmp_dict
        return id_list
        
    '''
    check around
    '''
    def run(self):
        # Initialization
        num_r = 0 # number of round
        vm_list = {} # list of vm
        op = Operation()
        
        while True:
            appendFile('Time: ' + time.asctime(time.localtime()) + ' >> ' + str(num_r) + '\n', self.logfile)
            
            id_list = self.chk_ins(int(time.time()))
            
            if id_list != None and len(id_list) != 0:   
                for vm_c in id_list: # Notice: vm_c is uuid
                    if vm_list.has_key(vm_c):
                        # Update
                        vm_list[vm_c]['ins_status'] = id_list[vm_c]['ins_status']
#                        vm_list[vm_c]['ins_hostname'] = id_list[vm_c]['ins_hostname']
                        vm_list[vm_c]['chk_time'] = id_list[vm_c]['chk_time'] #Check time
                        
                        
                        vm_list[vm_c]['cpu_usage'] = id_list[vm_c]['cpu_usage']
                        vm_list[vm_c]['mem_free'] = id_list[vm_c]['mem_free']
                        vm_list[vm_c]['mem_max'] = id_list[vm_c]['mem_max']
                        vm_list[vm_c]['nic_in'] = id_list[vm_c]['nic_in']
                        vm_list[vm_c]['nic_out'] = id_list[vm_c]['nic_out']
                        vm_list[vm_c]['disk_read'] = id_list[vm_c]['disk_read']
                        vm_list[vm_c]['disk_write'] = id_list[vm_c]['disk_write']
                        
                        # Last report time by kanyun
                        if vm_list[vm_c]['monitor_time'] == id_list[vm_c]['monitor_time']:
                            # add repeat num
                            vm_list[vm_c]['repeat_num'] = vm_list[vm_c]['repeat_num'] + 1
                            
                            # Alarm threshold 5
                            if vm_list[vm_c]['repeat_num'] <= self.wait:
                                appendFile(vm_c + ' - [WAITING - ' + str(vm_list[vm_c]['repeat_num']) + '][' + vm_list[vm_c]['ins_status'] + ']\n', self.logfile)
                            elif vm_list[vm_c]['repeat_num'] > self.wait and vm_list[vm_c]['repeat_num'] <= self.reboot:
                                appendFile(vm_c + ' - [FAILED - ' + str(vm_list[vm_c]['repeat_num']) + '][' + vm_list[vm_c]['ins_status'] + ']\n', self.logfile)
                            else:
                                #TODO: Further operation like reboot, migration and so on
                                op.reboot_ins(vm_c)
                                appendFile(vm_c + ' - [REBOOT][' + vm_list[vm_c]['ins_status'] + ']\n', self.logfile)
                        else:
                            # set repeat num to zero
                            vm_list[vm_c]['repeat_num'] = 0
                            vm_list[vm_c]['monitor_time'] = id_list[vm_c]['monitor_time'] 
                            appendFile(vm_c + ' - [OK][' + vm_list[vm_c]['ins_status'] + ']\n', self.logfile)
                    else:
                        # Insert
                        tmp_dict = {}
                        tmp_dict['ins_name'] = id_list[vm_c]['ins_name']
                        tmp_dict['ins_status'] = id_list[vm_c]['ins_status']
#                        tmp_dict['ins_hostname'] = rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 show " + tmp_dict['ins_uuid'] + " | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}'").strip()

                        tmp_dict['cpu_usage'] = id_list[vm_c]['cpu_usage']
                        tmp_dict['mem_free'] = id_list[vm_c]['mem_free']
                        tmp_dict['mem_max'] = id_list[vm_c]['mem_max']
                        tmp_dict['nic_in'] = id_list[vm_c]['nic_in']
                        tmp_dict['nic_out'] = id_list[vm_c]['nic_out']
                        tmp_dict['disk_read'] = id_list[vm_c]['disk_read']
                        tmp_dict['disk_write'] = id_list[vm_c]['disk_write']
                        
                        tmp_dict['chk_time'] = id_list[vm_c]['chk_time']
                        tmp_dict['monitor_time'] = id_list[vm_c]['monitor_time']
                        tmp_dict['repeat_num'] = 0
                        appendFile(vm_c + ' - [NEW][' + id_list[vm_c]['ins_status'] + ']\n', self.logfile)
                        
                        vm_list[vm_c] = tmp_dict
                    
            time.sleep(self.intvl)
            num_r = num_r + 1

if __name__ == "__main__":
    daemon = TestDaemon(pidfile='/tmp/daemon-example.pid', 
                        intvl=10, 
                        wait=4, 
                        reboot=7, 
                        logfile='/tmp/vm_monitor.log')
    
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print 'Unknown command'
            sys.exit(2)
    else:
        print 'USAGE: %s start/stop/restart' % sys.argv[0]
        sys.exit(2)
