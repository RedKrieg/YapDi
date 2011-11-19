# !/usr/bin/env python
''' 
#
# YapDi - Yet another python Daemon implementation
# Author Kasun Herath <kasunh01@gmail.com> 
#
'''

from signal import SIGTERM
import sys, atexit, os, pwd
import inspect
import time

class Daemon:
    def __init__(self, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        # called module name is used to write the file used to store process id
        self.called_module = self.get_calledmodule()
        self.pidfile = self.get_pidfile(self.called_module)

        # user to run under
        self.daemon_user = None

    def daemonize(self):
        ''' Daemonize the called module '''
        if self.status():
            message = "Is instance of %s already running?\n" % self.called_module
            sys.stderr.write(message)
            return False
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            return False

        # decouple from parent environment
        os.setsid() 
        os.umask(0)

        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            return False

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
    
        # If daemon user is set change current user to self.daemon_user
        if self.daemon_user:
            try:
                uid = pwd.getpwnam(self.daemon_user)[2]
                os.setuid(uid)
            except NameError, e:
                return False
            except OSError, e:
                return False
        return True

    def delpid(self):
        os.remove(self.pidfile)

    def kill(self):
        ''' kill running instance '''
        # check if an instance is not running
        pid = self.status()
        if not pid:
            message = "Instance of %s not running?\n" % self.called_module
            sys.stderr.write(message)
            return False

        # Try killing the daemon process	
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                return False
        return True

    def restart(self):
        ''' Restart an instance '''
        if self.status():
            self.kill()
        self.daemonize()

    def status(self):
        ''' check whether an instance is already running. If running return pid and else False '''
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        return pid

    def set_user(self, username):
        ''' Set user under which the daemonized process should run '''
        if not isinstance(username, str):
            raise TypeError('username should be of type str')
        self.daemon_user = username

    def get_calledmodule(self):
        ''' Returns original called module '''
        called_modulepath = inspect.stack()[-1][1]
        called_module = os.path.split(called_modulepath)[1].split('.')[0]
        return called_module

    def get_pidfile(self, module):
        ''' Return file name to save pid given a module '''
        return ('.%s.pid' % (module,))
