#!/usr/bin/env python
'''
Created on Apr 1, 2013

@author: jingshao@cnic.cn
'''

#import MySQLdb
import string, json

'''
Append content after file
'''
def appendFile(content, filename):
    if len(content) != 0:
        output = open(filename, 'a')
        output.write(content)
        output.close()
    else:
        return

'''
Remove continue space in string
'''
def rmSp(s, sep=None):
    return (sep or ' ').join(x for x in s.split(sep))

'''
Print DICT in json format
'''
def printDict(objDict):
    jsonDumpsIndentStr = json.dumps(objDict, indent=1)
    print jsonDumpsIndentStr
    
'''
Read config parameters from *.config
'''    
def readParameters(filename):
#        print 'read parameters from ' + filename
    f = open(filename, 'r')
    param = {}
    
    try:
        currentLine = f.readline().strip()
        while currentLine:
#                print current_line
            if currentLine != '' and currentLine != '\n':
                tmps = currentLine.split('=')
                if tmps != None and len(tmps) == 2:
                    if tmps[0].startswith('$'):
                        param[tmps[0][1:len(tmps[0])]] = string.atoi(tmps[1].strip())
                    else:
                        param[tmps[0]] = tmps[1].strip()
            
            currentLine = f.readline()
    except Exception, e:
        print 'Error @ line: ' + currentLine
        print str(e)
        return None
    f.close()
    return param
    
if __name__ == '__main__':
#    print ("nova --os-username %s --os_password %s --os_tenant_name %s --os_auth_url %s list " % ('str1', 'str2', 'str3', 'str4'))
    printDict(readParameters('vmmonitor.config'))
    pass
        
