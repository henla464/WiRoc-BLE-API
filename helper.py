#!/usr/bin/env python3

import os
from subprocess import Popen

URIPATH = 'http://127.0.0.1:5000/api/'

class Helper:
    @staticmethod
    def upgradeWiRocPython(version):
        print("helper.upgradeWiRocPython")
        logfile = '../installWiRocPython.log'
        print(os.getcwd())
        with open(os.devnull, 'r+b', 0) as DEVNULL:
            with open(logfile, 'a') as out:
                p = Popen(['./installWiRocPython.sh %s' % version], shell=True, stdin=DEVNULL, stdout=out, stderr=out, close_fds=True, cwd='..')

        return 'OK'
