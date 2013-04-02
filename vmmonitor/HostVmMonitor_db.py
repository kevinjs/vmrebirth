#!/usr/bin/env python
'''
Created on Mar 31, 2013

@author: jingshao@cnic.cn

ECCP - ZeData
'''

import sys, time, datetime
import json, MySQLdb, redis
import copy

from DaemonClass import Daemon
from RunCommandClass import RunCommand
from OperationClass import Operation
#from NovaDbUtil import DbUtil

def rm_sp(s, sep=None):
    return (sep or ' ').join(x for x in s.split(sep))

def appendFile(content, filename):
    if len(content) != 0:
        output = open(filename, 'a')
        output.write(content)
        output.close()
    else:
        return

class HostVmMonitor(Daemon):
    '''
    doc
    '''
    def __init__(self,  
             pidfile='/tmp/example.pid',
             stdin='/dev/stdin', 
             stdout='/dev/stdout', 
             stderr='/dev/stderr', 
             intvl=10, 
             reboot=10,
             logfile='ECCP_Monitor.log'):
    
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        
        self._rc = RunCommand()
#        self._dbUtil = DbUtil()
        
        self._host_list = {}
        self._vm_list = {}
        self._report = {}
        self._reboot_threshold = reboot
        self._check_interval = intvl
        
        self.logfile = logfile
    
    
    def _find_host(self, ins_uuid):
        conn_mysql = MySQLdb.connect(host='192.168.138.32', user='root', passwd='csdb123cnic', db='nova', port=3306)
        
        cur = conn_mysql.cursor()
        n = cur.execute("select host from instances where uuid = '%s' " % ins_uuid)
        
        _host_name = None
        
        if n == 0:
            return None
        else:
            _host_name = cur.fetchone()[0]
            
        cur.close()
        conn_mysql.close()
        
        return _host_name
    
    '''
    Check all available hosts
    '''
    def check_host(self, chk_timestamp):
#        rc = RunCommand()
        tmp = self._rc.run("nova-manage service list ")
        tmps = tmp.strip().split('\n')
        host_list = {}

        for line in tmps[1:len(tmps)]:
            term = rm_sp(line).split(' ')
            
            state_str = ''    
            if term[len(term)-3] == ':-)':
                state_str = 'ALIVE'
            else:
                state_str = 'NON-ALIVE'
            
            if host_list.has_key(term[1]):
                host_list[term[1]]['SERVICE'].append({'NAME':term[0], 'STATE':state_str})
            else:
                temp = {}
                
                temp['SERVICE'] = []
                temp['CHECK_TIMESTAMP'] = chk_timestamp
#                temp['SERVICE'].append({'NAME':term[0], 'STATE':term[len(term)-3], 'STATUS':term[len(term)-4]})
                temp['SERVICE'].append({'NAME':term[0], 'STATE':state_str})
                host_list[term[1]] = temp
        
        # Update global host_list 
        _tmp_host_list = list(set(self._host_list.keys()).union(set(host_list.keys())))
        
        for host in _tmp_host_list:
            self._report[host] = {}
            # old
            if self._host_list.has_key(host) and host_list.has_key(host):
                self._host_list[host] = copy.deepcopy(host_list.get(host))
                self._host_list[host]['AVAILABLE'] = True
            # new
            elif (not self._host_list.has_key(host)) and host_list.has_key(host):
                self._host_list[host] = copy.deepcopy(host_list.get(host))
                self._host_list[host]['AVAILABLE'] = True
            # Not available
            elif self._host_list.has_key(host) and (not host_list.has_key(host)):
                self._host_list[host] = {}
                self._host_list[host]['AVAILABLE'] = False
                
            _host_state = 'ALIVE'
            for serv in self._host_list[host]['SERVICE']:
                if serv['STATE'] == 'NON-ALIVE':
                    _host_state = 'NON-ALIVE'
                    break
                
            self._report[host]['status'] = _host_state
            self._report[host]['vm_list'] = []
        
    '''
    Check all virtual machines
    '''
    def check_vm(self, chk_timestamp):
        tmp = self._rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 list ")
        tmps = tmp.strip().split('\n')
        
        id_list = {}
        redis_c = redis.Redis(host='127.0.0.1', port=6379)
        
        for line in tmps:
            if not line.startswith('+'):
                line_s = line.strip().split('|')
                if line_s[1].strip() != 'ID':
                    tmp_dict = {}
                    tmp_dict['ins_uuid'] = line_s[1].strip()
                    tmp_dict['ins_name'] = line_s[2].strip()
                    tmp_dict['ins_status'] = line_s[3].strip()
#                    tmp_dict['ins_hostname'] = self._rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 show " + tmp_dict['ins_uuid'] + " | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}'").strip()
                    tmp_dict['ins_hostname'] = self._find_host(tmp_dict['ins_uuid'])
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
        
        # Update global vm_list
        if id_list != None and len(id_list) != 0:
            for vm_c in id_list: # Notice: vm_c is uuid
                if self._vm_list.has_key(vm_c):
                    # Update
                    self._vm_list[vm_c]['ins_status'] = id_list[vm_c]['ins_status']
                    self._vm_list[vm_c]['ins_hostname'] = id_list[vm_c]['ins_hostname']
                    self._vm_list[vm_c]['chk_time'] = id_list[vm_c]['chk_time'] #Check time
		    
		    if id_list[vm_c].has_key('cpu_usage'):                    
                        self._vm_list[vm_c]['cpu_usage'] = id_list[vm_c]['cpu_usage']
                        self._vm_list[vm_c]['mem_free'] = id_list[vm_c]['mem_free']
                        self._vm_list[vm_c]['mem_max'] = id_list[vm_c]['mem_max']
                        self._vm_list[vm_c]['nic_in'] = id_list[vm_c]['nic_in']
                        self._vm_list[vm_c]['nic_out'] = id_list[vm_c]['nic_out']
                        self._vm_list[vm_c]['disk_read'] = id_list[vm_c]['disk_read']
                        self._vm_list[vm_c]['disk_write'] = id_list[vm_c]['disk_write']
                    
                    # Last report time by kanyun
                    if self._vm_list[vm_c]['monitor_time'] == id_list[vm_c]['monitor_time']:
                        # add repeat num
                        self._vm_list[vm_c]['repeat_num'] = self._vm_list[vm_c]['repeat_num'] + 1
                        self._report[self._vm_list[vm_c]['ins_hostname']]['vm_list'].append({'vm':vm_c, 'status':'WAITING', 'repeat_num': self._vm_list[vm_c]['repeat_num'], 'status-ori':self._vm_list[vm_c]['ins_status']})
                    else:
                        # set repeat num to zero
                        self._vm_list[vm_c]['repeat_num'] = 0
                        self._vm_list[vm_c]['monitor_time'] = id_list[vm_c]['monitor_time']
                        self._report[self._vm_list[vm_c]['ins_hostname']]['vm_list'].append({'vm':vm_c, 'status':'OK', 'repeat_num': self._vm_list[vm_c]['repeat_num'], 'status-ori':self._vm_list[vm_c]['ins_status']})   
                else:
                    # Insert
                    tmp_dict = {}
                    tmp_dict['ins_uuid'] = id_list[vm_c]['ins_uuid']
                    tmp_dict['ins_name'] = id_list[vm_c]['ins_name']
                    tmp_dict['ins_status'] = id_list[vm_c]['ins_status']
#                    tmp_dict['ins_hostname'] = self._rc.run("nova --os-username admin --os_password csdb123cnic --os_tenant_name admin --os_auth_url http://192.168.138.32:5000/v2.0 show " + tmp_dict['ins_uuid'] + " | grep OS-EXT-SRV-ATTR:hypervisor_hostname | awk '{print $4}'").strip()
                    tmp_dict['ins_hostname'] = self._find_host(tmp_dict['ins_uuid'])

#		     print id_list[vm_c]
		    if id_list[vm_c].has_key('cpu_usage'):
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
                    
                    self._vm_list[vm_c] = tmp_dict
                    self._report[self._vm_list[vm_c]['ins_hostname']]['vm_list'].append({'vm':vm_c, 'status':'NEW', 'repeat_num': self._vm_list[vm_c]['repeat_num'], 'status-ori':self._vm_list[vm_c]['ins_status']})
    '''
    Chech around
    '''
    def run(self):
        num_r = 0
        op = Operation()
        
        while True:
            self._report = {}
            chk_timestamp = int(time.time())
            appendFile('Time: ' + time.asctime(time.localtime()) + ' >> ' + str(num_r) + '\n', self.logfile)
            
            self.check_host(chk_timestamp)
            self.check_vm(chk_timestamp)
            
            if self._report != None and len(self._report) != 0:
                for host in self._report:
                    appendFile('Host: ' + host + ' -- Status: ' + self._report[host]['status'] + '\n', self.logfile)
                    
                    if self._report[host]['status'] != 'ALIVE':
                        appendFile('  - TODO: Migration...\n', self.logfile)
                    else:
                        for vm in self._report[host]['vm_list']:
                            appendFile('  - ' + vm['vm'] + ' [' + vm['status'] + ' - ' + str(vm['repeat_num']) + '][' + vm['status-ori'] + ']\n', self.logfile)
                            
                            if vm['status'] == 'WAITING' and vm['repeat_num'] > self._reboot_threshold:
                                op.reboot_ins(vm['vm'])
                                
            time.sleep(self._check_interval)
            num_r = num_r + 1


            
if __name__ == "__main__":
    daemon = HostVmMonitor(pidfile='/tmp/daemon-example.pid', 
                           intvl=15,  
                           reboot=5, 
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
