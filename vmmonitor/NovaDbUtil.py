#!/usr/bin/env python
'''
Created on Apr 1, 2013

@author: jingshao@cnic.cn
'''

import MySQLdb

class DbUtil:
    '''
    classdocs
    '''

#    def __init__(self):
#        '''
#        Constructor
#        '''
        
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
    
if __name__ == '__main__':
    db = DbUtil()
    
    print db._find_host('259c78f2-fdeb-4dc1-b0cf-9c92e203c0f1')
    
    pass
        
