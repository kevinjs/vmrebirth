#!/usr/bin/env python

import StringIO, sys, string
import os, subprocess

class RunCommand:

    def run(self, cmd):
        shell = False
        
        if type(cmd) == type('str'):
            shell = True
        else:
            paths = os.environ['PATH'].split(':')
            app = cmd[0]
            for path in paths:
                rapp = os.path.join(path, app)
                if os.path.exists(rapp):
                    cmd[0] = rapp
                    break
        
        try:
            proc = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=sys.stderr)
            proc.wait()
        except Exception, e:
            raise Exception("Could not perform command [%s]: %s" % (cmd, e))
        
        sbuf = StringIO.StringIO()
        
        for line in proc.stdout:
            sbuf.write(line)
        
        return sbuf.getvalue()
