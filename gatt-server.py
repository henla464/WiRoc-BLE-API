#!/usr/bin/env python3

import requests
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import uuid
import json
from gatt import *
from helper import Helper
from advertisement import *
from gi.repository import GLib
import sys

from random import randint

mainloop = None

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DEVICE1_IFACE = 'org.bluez.Device1'

API_SERVICE = 'fb880900-4ab2-40a2-a8f0-14cc1c2e5608'

URIPATH = 'http://127.0.0.1:5000/api/'

device = None
ad_manager =  None
service_manager = None
wiroc_application = None
wiroc_advertisement = None

class WiRocApplication(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(ApiService(bus, 0))

        bus.add_signal_receiver(self.InterfacesAdded,
                                dbus_interface="org.freedesktop.DBus.ObjectManager",
                                signal_name="InterfacesAdded")

        bus.add_signal_receiver(self.InterfacesRemoved,
                                dbus_interface="org.freedesktop.DBus.ObjectManager",
                                signal_name="InterfacesRemoved")

        bus.add_signal_receiver(self.PropertiesChanged,
                                dbus_interface="org.freedesktop.DBus.Properties",
                                signal_name="PropertiesChanged",
                                arg0="org.bluez.Device1",
                                path_keyword="path")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)


    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response

    def PrintNormal(self, properties):
        if "Address" in properties:
            address = properties["Address"]
        else:
            address = "<unknown>"

        print("[ " + address + " ]")

        for key in properties.keys():
            value = properties[key]
            if type(value) is dbus.String:
                value = value.encode('ascii', 'replace')
            if (key == "Class"):
                print("    %s = 0x%06x" % (key, value))
            else:
                print("    %s = %s" % (key, value))

        print()
        properties["Logged"] = True

    def InterfacesAdded(self, path, interfaces):
        global device
        print('interfaces added')
        properties = None
        if DEVICE1_IFACE in interfaces:
            properties = interfaces[DEVICE1_IFACE]
            if not properties:
                return

        if 'org.bluez.GattService1' in interfaces:
            properties = interfaces['org.bluez.GattService1']
            if not properties:
                return

        if 'org.bluez.GattCharacteristic1' in interfaces:
            properties = interfaces['org.bluez.GattCharacteristic1']
            if not properties:
                return

        if properties == None:
            for k, v in interfaces.items():
                print(k, v)
        else:
            self.PrintNormal(properties)


    def InterfacesRemoved(self, path, interfaces):
        global device
        print('interfaces removed')
        print("removed: ")
        print(*interfaces, sep="\n")



    def PropertiesChanged(self, interface, changed, invalidated, path):
        global device
        print('properties changed')
        print('Interface: ' + interface)
        if interface != DEVICE1_IFACE:
            return

        print("Invalidated:")
        print(*invalidated, sep="\n")

        self.PrintNormal(changed)


class ApiService(Service):
    """
        Single service with a few characteristics to read/write properties
        Execute commands
        Listen to punches and
        Test send punches
    """
    SERVICE_UUID = API_SERVICE

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID, True)
        self.add_characteristic(PropertiesCharacteristic(bus, 0, self))
        self.add_characteristic(CommandCharacteristic(bus, 1, self))
        self.add_characteristic(PunchesCharacteristic(bus, 2, self))
        self.add_characteristic(TestPunchesCharacteristic(bus, 3, self))


#---- PROPERTIES -----
class PropertiesCharacteristic(Characteristic):
    """
        Write a new property value, or read one
    """
    UUID = 'FB880912-4AB2-40A2-A8F0-14CC1C2E5608'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.UUID,
                ['write', 'notify'],
                service)
        self.add_descriptor(DescriptionDescriptor(bus, 0, self, 'Write a new property value, or read one'))
        # presentation format: 0x19 = utf8, 0x01 = exponent 1, 0x00 0x27 = unit less, 0x01 = namespace, 0x00 0x00 description
        self.add_descriptor(PresentationDescriptor(bus, 1, self, [dbus.Byte(0x19), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x27), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x00)]))
        self._nofitying = False


    def notify(self, replyString):
        if not self._nofitying:
            return
        reply = replyString.encode()
        while len(reply) > 0:
            subReply = reply[0:512]
            reply = reply[512:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])


    def WriteValue(self,value, options):
        try:
            print('PropertiesCharacteristic - onWriteRequest')
            propertyNameAndValues = bytes(value).decode()
            thisFnCallPropertyNameAndValuesToWriteArr = propertyNameAndValues.split('|')
            print(thisFnCallPropertyNameAndValuesToWriteArr)
            for propAndVal in thisFnCallPropertyNameAndValuesToWriteArr:
                propAndValArr = propAndVal.split(';')
                propName = propAndValArr[0]
                propVal = None
                print(propName)
                uri = URIPATH + propName + '/'
                if len(propAndValArr) > 1:
                    propVal = propAndValArr[1]
                if (propVal != None and len(propVal) > 0):
                    uri += propVal + '/'
                print(uri)
                req = requests.get(uri)
                returnValue = propName + ';' + str(req.json()['Value']) + '|'
                print('returnValue ' + str(returnValue))
                self.notify(returnValue)
        except:
            e = sys.exc_info()[0]
            print("exception " + str(e))
            self.notify('')


    def StartNotify(self):
        if self._nofitying:
            print('Prop: Already notifying, nothing to do')
            return
        print('Start notifying')
        self._nofitying = True


    def StopNotify(self):
        if not self._nofitying:
            print('Prop: Not notifying, nothing to do')
            return
        print('Stop notifying')
        self._nofitying = False


#---- COMMAND -----
class CommandCharacteristic(Characteristic):
    """
        Write a new property value, or read one
    """
    UUID = 'FB880913-4AB2-40A2-A8F0-14CC1C2E5608'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.UUID,
                ['write', 'notify'],
                service)
        self.add_descriptor(DescriptionDescriptor(bus, 0, self, 'Execute a command'))
        # presentation format: 0x19 = utf8, 0x01 = exponent 1, 0x00 0x27 = unit less, 0x01 = namespace, 0x00 0x00 description
        self.add_descriptor(PresentationDescriptor(bus, 1, self, [dbus.Byte(0x19), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x27), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x00)]))
        self._nofitying = False

    def notify(self, replyString):
        if not self._nofitying:
            return
        reply = replyString.encode()
        while len(reply) > 0:
            subReply = reply[0:512]
            reply = reply[512:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])

    def WriteValue(self, value, options):
        try:
            print('CommandCharacteristic - onWriteRequest')
            cmdAndValue = bytes(value).decode()
            print(cmdAndValue)
            cmdAndValuesArr = cmdAndValue.split(';')
            cmdName = cmdAndValuesArr[0]
            commandValue = None
            print(cmdName)
            if len(cmdAndValuesArr) > 1:
                commandValue = cmdAndValuesArr[1]
            print('writevalue 2')

            replyString = ''

            if cmdName =='listwifi':
                replyString = Helper.getListWifi()
            elif cmdName =='connectwifi':
                replyString = Helper.connectWifi(commandValue )
            elif cmdName == 'disconnectwifi':
                replyString = Helper.disconnectWifi()
            elif cmdName == 'getip':
                replyString = Helper.getIP()
            elif cmdName == 'renewip':
                replyString = Helper.renewIP(commandValue )
            elif cmdName =='getservices':
                replyString = Helper.getServices()
            elif cmdName =='dropalltables':
                replyString = Helper.dropAllTables()
            elif cmdName =='uploadlogarchive':
                replyString = Helper.uploadLogArchive()
            elif cmdName =='upgradewirocpython':
                replyString = Helper.upgradeWiRocPython(commandValue)
            elif cmdName =='upgradewirocble':
                replyString = Helper.upgradeWiRocBLE(commandValue )
            elif cmdName =='getall':
                replyString = Helper.getAll()
            elif cmdName =='batterylevel':
                replyString = Helper.getBatteryLevel()

            replyString = cmdName + ';' + replyString
            print(replyString)
            self.notify(replyString)
        except:
            print("exception write value")

    def StartNotify(self):
        if self._nofitying:
            print('Already notifying, nothing to do')
            return
        print('Start notifying')
        self._nofitying = True

    def StopNotify(self):
        if not self._nofitying:
            print('Not notifying, nothing to do')
            return
        print('Stop notifying')
        self._nofitying = False

#---- PUNCHES -----
class PunchesCharacteristic(Characteristic):
    """
        Write a new property value, or read one
    """
    UUID = 'FB880901-4AB2-40A2-A8F0-14CC1C2E5608'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.UUID,
                ['notify'],
                service)
        self.add_descriptor(DescriptionDescriptor(bus, 0, self, 'Sends out the punch data'))
        # presentation format: 0x19 = utf8, 0x01 = exponent 1, 0x00 0x27 = unit less, 0x01 = namespace, 0x00 0x00 description
        self.add_descriptor(PresentationDescriptor(bus, 1, self, [dbus.Byte(0x19), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x27), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x00)]))

        self._nofitying = False
        self._timeoutSourceId = None

    def notify(self, replyString):
        if not self._nofitying:
            return
        reply = replyString.encode()
        while len(reply) > 0:
            subReply = reply[0:512]
            reply = reply[512:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])

    def getPunches(self):
        uri = URIPATH + 'punches/'
        req = requests.get(uri)
        thePunches = req.json()['Value']
        thePunches = thePunches[len('punches;')]
        self.notify(thePunches)
        return True

    def StartNotify(self):
        if self._nofitying:
            print('PunchesCharacteristic - Already notifying, nothing to do')
            return
        print('PunchesCharacteristic - Start notifying')
        uri = URIPATH + 'sendtoblenoenabled/1'
        req = requests.get(uri)
        self._nofitying = True
        self._timeoutSourceId = GLib.timeout_add(1000, self.getPunches())

    def StopNotify(self):
        if not self._nofitying:
            print('PunchesCharacteristic - Not notifying, nothing to do')
            return
        print('PunchesCharacteristic - Stop notifying')
        GLib.source_remove(self._timeoutSourceId)
        uri = URIPATH + 'sendtoblenoenabled/0'
        req = requests.get(uri)
        self._nofitying = False

#---- TESTPUNCHES -----
class TestPunchesCharacteristic(Characteristic):
    """
        Write a new property value, or read one
    """
    UUID = 'FB880907-4AB2-40A2-A8F0-14CC1C2E5608'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.UUID,
                ['read', 'write', 'notify'],
                service)
        self.add_descriptor(DescriptionDescriptor(bus, 0, self, 'Send test punches'))
        # presentation format: 0x19 = utf8, 0x01 = exponent 1, 0x00 0x27 = unit less, 0x01 = namespace, 0x00 0x00 description
        self.add_descriptor(PresentationDescriptor(bus, 1, self, [dbus.Byte(0x19), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x27), dbus.Byte(0x01), dbus.Byte(0x00), dbus.Byte(0x00)]))

        self._notifying = False
        self._timeoutSourceIdGetPunches = None
        self._timeoutSourceIdAddPunches = None
        self._testBatchGuid = None
        self._siNo = None
        self._noOfPunchesToAdd = 0
        self._noOfPunchesAdded = 0

    def notify(self, replyString):
        if not self._nofitying:
            return
        reply = replyString.encode()
        while len(reply) > 0:
            subReply = reply[0:512]
            reply = reply[512:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])

    def getTestPunches(self):
        print('getTestPunches')
        try:
            if self._testBatchGuid == None:
                print("self._testBatchGuid is None")
                return True

            includeAll = False
            uri = URIPATH + 'testpunches/gettestpunches/' + str(self._testBatchGuid) + '/' + ("true" if includeAll else "false") + '/'
            resp = requests.get(uri)
            replyString = resp.json()['punches']
            print(replyString)
            replyString2 = json.dumps(replyString)
            self.notify(replyString2)
        except:
            print('exception in getTestPunches')
        finally:
            return True

    def addTestPunch(self):
        try:
            # add punch
            print("addTestPunch")

            uri = URIPATH + 'testpunches/addtestpunch/' + str(self._testBatchGuid) + '/' + self._siNo + '/'
            resp = requests.get(uri)
            print(resp.json())

            self._noOfPunchesAdded = self._noOfPunchesAdded + 1
            if self._noOfPunchesAdded >= self._noOfPunchesToAdd:
                print("addTestPunchInterval cleared")
                if self._timeoutSourceIdAddPunches != None:
                    GLib.source_remove(self._timeoutSourceIdAddPunches)
                    self._timeoutSourceIdAddPunches = None
                return False
        except:
            print('exception in addTestPunch')
        finally:
            return True

    def WriteValue(self,value, options):
        try:
            print('TestPunchesCharacteristic - onWriteRequest')

            noOfPunchesAndIntervalAndSINo = bytes(value).decode()
            print(noOfPunchesAndIntervalAndSINo)
            self._noOfPunchesToAdd = int(noOfPunchesAndIntervalAndSINo.split(';')[0])
            self._noOfPunchesAdded = 0
            intervalMs = 1000
            if len(noOfPunchesAndIntervalAndSINo.split(';')) > 1:
                intervalMs = int(noOfPunchesAndIntervalAndSINo.split(';')[1])
            if len(noOfPunchesAndIntervalAndSINo.split(';')) > 2:
                self._siNo = noOfPunchesAndIntervalAndSINo.split(';')[2]

            #if self._timeoutSourceIdGetPunches != None:
            #    GLib.source_remove(self._timeoutSourceIdGetPunches)
            #    self._timeoutSourceIdGetPunches = None
            if self._timeoutSourceIdAddPunches != None:
                GLib.source_remove(self._timeoutSourceIdAddPunches)
                self._timeoutSourceIdAddPunches = None

            print("Number of punches to add: " + str(self._noOfPunchesToAdd) + " interval: " + str(intervalMs) + " si number: " + self._siNo)
            self._testBatchGuid = uuid.uuid4()
            self._timeoutSourceIdAddPunches = GLib.timeout_add(1000, self.addTestPunch)
        except:
            print("exception")

    def ReadValue(self, options):
        includeAll = True
        uri = URIPATH + 'testpunches/gettestpunches/' + self._testBatchGuid + '/' + ("true" if includeAll else "false") + '/'
        resp = requests.get(uri)
        self.notify(resp.json()['Value'])

    def StartNotify(self):
        if self._notifying:
            print('TestPunches: Already notifying, nothing to do')
            return
        print('TestPunches: Start notifying')
        self._notifying = True
        self._timeoutSourceIdGetPunches = GLib.timeout_add(1000, self.getTestPunches)

    def StopNotify(self):
        if not self._notifying:
            print('TestPunches: Not notifying, nothing to do')
            return
        print('TestPunches: Stop notifying START')
        GLib.source_remove(self._timeoutSourceIdGetPunches)
        self._timeoutSourceIdGetPunches = None
        if self._timeoutSourceIdAddPunches != None:
            GLib.source_remove(self._timeoutSourceIdAddPunches)
            self._timeoutSourceIdAddPunches = None
        self._notifying = False
        print('TestPunches: Stop notifying END')


class WiRocAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid(API_SERVICE)
        #self.add_service_uuid('180F')
        #self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        #self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        #self.add_service_data('9999', [0x00, 0x01, 0x02])

        uri = URIPATH + 'wirocdevicename/'
        print(uri)
        req = requests.get(uri)
        self.add_local_name(req.json()['Value'])
        #self.add_local_name('Test')
        self.include_tx_power = True
        #self.add_data(0x26, [0x01, 0x01, 0x00])


def register_ad_cb():
    print('Advertisement registered')

def register_ad_error_cb(error):
    print('Failed to register advertisement: ' + str(error))
    mainloop.quit()

def register_app_cb():
    print('GATT application registered')

def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None

def find_device1(bus):
    om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, interfaces in objects.items():
        if "org.bluez.Device1" in interfaces:
            return interfaces["org.bluez.Device1"]

    return None

def main():
    try:
        global mainloop

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        bus = dbus.SystemBus()

        adapter = find_adapter(bus)
        global device
        device = find_device1(bus)

        if not adapter:
            print('GattManager1 interface not found')
            return

        global service_manager
        service_manager = dbus.Interface(
                bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                GATT_MANAGER_IFACE)

        global wiroc_application
        wiroc_application = WiRocApplication(bus)

        global ad_manager
        ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                    LE_ADVERTISING_MANAGER_IFACE)

        global wiroc_advertisement
        wiroc_advertisement = WiRocAdvertisement(bus, 0)

        mainloop = GLib.MainLoop()


        try:
            path = wiroc_advertisement.get_path()
            print('Path: ' + path)
            print('Registering advertisement')
            ad_manager.RegisterAdvertisement(wiroc_advertisement.get_path(), {},
                                         reply_handler=register_ad_cb,
                                         error_handler=register_ad_error_cb)
            print('After Registering advertisement')
        except:
            print('Advertisement exception')
            ad_manager.UnregisterAdvertisement(wiroc_advertisement)
            print('Advertisement unregistered')
            dbus.service.Object.remove_from_connection(wiroc_advertisement)

        print('Registering GATT application...')
        service_manager.RegisterApplication(wiroc_application.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)




        mainloop.run()
        print("after mainLoop")
        #ad_manager.UnregisterAdvertisement(wiroc_advertisement)
        #service_manager.UnregisterApplication(app)
        #print('Advertisement unregistered')
        #dbus.service.Object.remove_from_connection(wiroc_advertisement)
    except (KeyboardInterrupt, SystemExit):
        ad_manager.UnregisterAdvertisement(wiroc_advertisement)
        dbus.service.Object.remove_from_connection(wiroc_advertisement)
        service_manager.UnregisterApplication(wiroc_application)
        dbus.service.Object.remove_from_connection(wiroc_application)
        mainloop.quit()
        print("KeyboardInterrupt/SystemExit")


if __name__ == '__main__':
    main()


