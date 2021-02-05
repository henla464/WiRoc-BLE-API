#!/usr/bin/env python3

import requests
import subprocess
import json
import socket
import os, sys
from datetime import datetime
from subprocess import Popen

URIPATH = 'http://127.0.0.1:5000/api/'

class Helper:

    # @staticmethod
    # def getIP():
    #     result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, check=True)
    #     ip = result.stdout.decode('utf-8').strip()
    #     return ip
    #
    #
    # @staticmethod
    # def renewIP(commandValue):
    #     result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'device,type', 'device', 'status'], stdout=subprocess.PIPE, check=True)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #     devices = result.stdout.decode('utf-8').splitlines()[0, -1] # remove last empty element
    #     devices = [dev[40:] for dev in devices]
    #     ifaces = devices[::2]
    #     ifaceNetworkTypes = devices[1::2]
    #     for iface, ifaceNetworkType in zip(ifaces, ifaceNetworkTypes):
    #         if (commandValue == ifaceNetworkType):
    #             result2 = subprocess.run(['dhclient', '-v', '-1', iface], stdout=subprocess.PIPE, check=True)
    #             if result2.returncode != 0:
    #                 errStr = result2.stderr.decode('utf-8')
    #                 raise Exception("Error: " + errStr)
    #             resultStr = result2.stdout.decode('utf-8')
    #             print(resultStr)
    #             return 'OK'
    #     raise Exception("Error: No matching iface")
    #
    #
    # @staticmethod
    # def getServices():
    #     statusServices = []
    #     result = subprocess.run(['systemctl', 'is-active', 'WiRocPython.service'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     statusServices.append({'Name': 'WiRocPython', 'Status': result.stdout.decode('utf-8').strip('\n')})
    #
    #     result = subprocess.run(['systemctl', 'is-active', 'WiRocPythonWS.service'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     statusServices.append({'Name': 'WiRocPythonWS', 'Status': result.stdout.decode('utf-8').strip('\n')})
    #
    #     result = subprocess.run(['systemctl', 'is-active', 'blink.service'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     statusServices.append({'Name': 'WiRocMonitor', 'Status': result.stdout.decode('utf-8').strip('\n')})
    #     jsonStr = json.dumps({'services': statusServices })
    #     return jsonStr
    #
    #
    # @staticmethod
    # def getBTAddress():
    #     result = subprocess.run(['hcitool', 'dev'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     stdout = result.stdout.decode('utf-8').replace("Devices:", "")
    #     stdout = stdout.strip()
    #     btAddress = "NoBTAddress"
    #     stdoutWords = stdout.split("\t")
    #     if stdoutWords.length > 1 and len(stdoutWords[1]) == 17:
    #         btAddress = stdoutWords[1]
    #     return btAddress
    #
    #
    # @staticmethod
    # def getListWifi():
    #     #Get new wifi list
    #     result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'ssid,active,signal', 'device', 'wifi', 'list'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     wifiNetworks = result.stdout.decode('utf-8').splitlines()[0:-1] # remove last empty element
    #     wifiNetworks2 = [netName[40:].strip() for netName in wifiNetworks]
    #     wifiDataList = '\n'.join(wifiNetworks2)
    #     return wifiDataList
    #
    # @staticmethod
    # def connectWifi(commandValue):
    #     wlanIFace = 'wlan0'
    #
    #     wifiName = commandValue.splitlines()[0]
    #     wifiPassword = commandValue.splitlines()[1]
    #
    #     result = subprocess.run(['nmcli', 'device', 'wifi', 'connect', wifiName, 'password', wifiPassword, 'ifname', wlanIFace], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     return 'OK'
    #
    # @staticmethod
    # def disconnectWifi():
    #     wlanIFace = 'wlan0'
    #
    #     result = subprocess.run(['nmcli', 'device', 'disconnect', wlanIFace], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     return 'OK'
    #
    # @staticmethod
    # def getBatteryLevel():
    #     hostname = socket.gethostname()
    #     if hostname == "chip" or hostname == "nanopiair":
    #         print("chip or nanopi")
    #         result = subprocess.run(['/usr/sbin/i2cget', '-f', '-y', '0', '0x34', '0xb9'], stdout=subprocess.PIPE)
    #         if result.returncode != 0:
    #             print('return code not 0')
    #             errStr = result.stderr.decode('utf-8')
    #             raise Exception("Error: " + errStr)
    #
    #         intPercent = int(result.stdout.decode('utf-8').splitlines()[0], 0)
    #         print('Battery level - onReadRequest: value (dec)=' + str(intPercent))
    #         return str(intPercent)
    #     else:
    #         return '1'
    #
    # @staticmethod
    # def uploadLogArchive():
    #     print('Helper.uploadLogArchive')
    #     btAddress = Helper.getBTAddress()
    #     dateNow = datetime.now()
    #     zipFilePath = Helper.getZipFilePath(btAddress, dateNow)
    #
    #     Helper.zipLogArchive(zipFilePath)
    #
    #     uri = URIPATH + 'apikey/'
    #     req = requests.get(uri)
    #     apiKey = req.json()['Value']
    #
    #     uri = URIPATH + 'webserverurl/'
    #     req = requests.get(uri)
    #     serverUrl = req.json()['Value']
    #
    #     uri = URIPATH + 'webserverhost/'
    #     req = requests.get(uri)
    #     serverHost = req.json()['Value']
    #
    #     Helper.uploadLogArchive2(apiKey, zipFilePath, serverUrl, serverHost)
    #     return 'OK'
    #
    # @staticmethod
    # def getZipFilePath(btAddress, date):
    #     filePath = "/home/chip/LogArchive/LogArchive_" + btAddress + "_" + date.now.strftime(
    #         "%Y-%m-%d-%H:%M:%S") + ".zip"
    #     return filePath
    #
    # @staticmethod
    # def zipLogArchive(zipFilePath):
    #     result = subprocess.run(
    #         ['zip', zipFilePath, '/home/chip/WiRoc-Python-2/WiRoc.db', '/home/chip/WiRoc-Python-2/WiRoc.log*'],
    #         stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         print('Helper.zipLogArchive: error: ' + errStr)
    #         raise Exception("Error: " + errStr)
    #
    #     return 'OK'
    #
    # @staticmethod
    # def uploadLogArchive2(apiKey, filePath, serverUrl, serverHost):
    #     result = subprocess.run(
    #         ['curl', -X, 'POST', '"' + serverUrl + '/api/v1/LogArchives\"', '-H', '"host: ' + serverHost + '"', '-H',
    #          '"accept: application/json"', '-H', '"Authorization: ' + apiKey + '"', '-F',
    #          '"newfile=@' + filePath + '"'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         print('Helper.uploadLogArchive2: error: ' + errStr)
    #         raise Exception("Error: " + errStr)
    #
    #     stdout = result.stdout.decode('utf-8')
    #     if len(stdout) > 0:
    #         print(stdout)
    #     return 'OK'
    #
    # @staticmethod
    # def startPatchAP6212():
    #     hostname = socket.gethostname()
    #     if hostname != "nanopiair":
    #         return "OK" # only nanopiair needs patching
    #
    #     result = subprocess.run(
    #         ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         print('Helper.startPatchAP6212: error: ' + errStr)
    #
    #         result = subprocess.run(
    #             ['systemctl', 'start', 'ap6212-bluetooth'], stdout=subprocess.PIPE)
    #         if result.returncode != 0:
    #             errStr = result.stderr.decode('utf-8')
    #             print('Helper.startPatchAP6212: second try error: ' + errStr)
    #             raise Exception("Error: " + errStr)
    #
    #     stdout = result.stdout.decode('utf-8')
    #     if len(stdout) > 0:
    #         print(stdout)
    #     return 'OK'
    #
    #
    #
    # @staticmethod
    # def dropAllTables():
    #     # stop WiRoc-Python service
    #     result = subprocess.run(['systemctl', 'stop', 'WiRocPython.service'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     uri = URIPATH + 'dropalltables/'
    #     req = requests.get(uri)
    #     retVal1 = req.json()['Value']
    #
    #     result = subprocess.run(['systemctl', 'start', 'WiRocPython.service'], stdout=subprocess.PIPE)
    #     if result.returncode != 0:
    #         errStr = result.stderr.decode('utf-8')
    #         raise Exception("Error: " + errStr)
    #
    #     if retVal1 == 'OK':
    #         # start WiRoc-Python service
    #         return 'OK'
    #     else:
    #         # start WiRoc-Python service
    #         raise Exception("Error starting WiRocPython service")

    @staticmethod
    def upgradeWiRocPython(version):
        print("helper.upgradeWiRocPython")
        cwd = os.getcwd()
        print("current workdir: " + cwd)
        logfile = '../installWiRocPython.log'
        with open(os.devnull, 'r+b', 0) as DEVNULL:
            with open(logfile, 'a') as out:
                p = Popen(['../installWiRocPython.sh %s' % version], shell=True,
                      stdin=DEVNULL, stdout=out, stderr=out, close_fds=True)

        #time.sleep(1)  # give it a second to launch
        #if p.poll():  # the process already finished and it has nonzero exit code
        #    sys.exit(p.returncode)

        #spawn = require('child_process').spawn
        #path = require('path')
        #fs = require('fs')
        #parentDir = path.resolve(__dirname, '..')
        #logfile = path.join(parentDir, 'installWiRocPython.log')
        #out = fs.openSync(logfile, 'a')
        #err = fs.openSync(logfile, 'a')
        #child = spawn('./installWiRocPython.sh', [version], {
        #    detached: true,
        #    stdio: ['ignore', out, err],
        #    cwd: parentDir
        #})
        #child.unref()
        print("Spawned installWiRocPython.sh")
        return 'OK'


    @staticmethod
    def upgradeWiRocBLE(version):
        print("helper.upgradeWiRocBLE")
        cwd = os.getcwd()
        print("current workdir: " + cwd)
        logfile = '../installWiRocBLE.log'
        with open(os.devnull, 'r+b', 0) as DEVNULL:
            with open(logfile, 'a', 0) as out:
                p = Popen(['/usr/bin/python35', '../installWiRocBLE.sh', version],
                          stdin=DEVNULL, stdout=out, stderr=out, close_fds=True)

        #spawn = require('child_process').spawn
        #path = require('path')
        #fs = require('fs')
        #parentDir = path.resolve(__dirname, '..')
        #logfile = path.join(parentDir, 'installWiRocBLE.log')
        #out = fs.openSync(logfile, 'a')
        #err = fs.openSync(logfile, 'a')
        #child = spawn('./installWiRocBLE.sh', [version], {
        #    detached: true,
        #    stdio: ['ignore', out, err],
        #    cwd: parentDir
        #})
        #child.unref()
        #console.log("Spawned installWiRocBLE.sh")
        return 'OK'

