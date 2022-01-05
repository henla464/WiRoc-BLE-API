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
import threading

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
chunkLength = 20

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
        #self.add_characteristic(CommandCharacteristic(bus, 1, self))
        self.add_characteristic(PunchesCharacteristic(bus, 1, self))
        self.add_characteristic(TestPunchesCharacteristic(bus, 2, self))


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
        self._notifying = False
        self._lastWrittenValue = ""


    def notify(self, replyString):
        if not self._notifying:
            return
        reply = replyString.encode()
        if len(reply) % chunkLength == 0:
            reply.append(" ".encode()[0])
        while len(reply) > 0:
            subReply = reply[0:chunkLength]
            reply = reply[chunkLength:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])

    def doRequestInBackground(self, uri, propName):
        try:
            req = requests.get(uri)
            theValue = req.json()['Value']
            returnValue = propName + '\t'
            if isinstance(theValue, str):
                returnValue += theValue
            else:
                returnValue += json.dumps(theValue)
            print('returnValue ' + str(returnValue))
            self.notify(returnValue)

            if propName == 'wirocdevicename':
                global wiroc_advertisement
                wiroc_advertisement.updateLocalName()
                wiroc_advertisement.updateAdvertisement()
        except:
            e = sys.exc_info()[0]
            print("exception " + str(e))
            self.notify('')

    def WriteValue(self,value, options):
        try:
            print('PropertiesCharacteristic - onWriteRequest')
            for k, v in options.items():
                print(k, v)
            #print('MTU: ' + str(options['mtu']))
            #print('Offset: ' + str(options['offset']))
            propertyNameAndValues = bytes(value).decode()
            global chunkLength
            if len(propertyNameAndValues) < chunkLength:
                # final fragment received
                propertyNameAndValues = self._lastWrittenValue + propertyNameAndValues
                self._lastWrittenValue = ""
            else:
                # This is not the full value, wait for the next fragment
                self._lastWrittenValue = self._lastWrittenValue + propertyNameAndValues
                return

            #thisFnCallPropertyNameAndValuesToWriteArr = propertyNameAndValues.split('|')
            #print(thisFnCallPropertyNameAndValuesToWriteArr)
            #for propAndVal in thisFnCallPropertyNameAndValuesToWriteArr:
            propAndValArr = propertyNameAndValues.split('\t')
            propName = propAndValArr[0]
            propVal = None
            print(propName)
            if len(propAndValArr) > 1:
                propVal = propAndValArr[1]

            # Handle some special cases
            if propName == 'all':
                if propVal != None:
                    # the very first call will be to fetch 'all', this call should include
                    # the chunklength ie. the number of bytes that can be sent at a time
                    chunkLength = int(propVal)
                    print("chunklength: " + str(chunkLength))
                    propVal = None
            elif propName == 'upgradewirocpython':
                # Use helper function and then return instead of calling web service
                replyString = Helper.upgradeWiRocPython(propVal)
                print(propName + '\t' + replyString)
                self.notify(propName + '\t' + replyString)
                return

            uri = URIPATH + propName + '/'
            if (propVal != None and len(propVal) > 0):
                uri += propVal + '/'
            print(uri)

            requestThread = threading.Thread(target=self.doRequestInBackground, name="Downloader", args=(uri, propName))
            requestThread.start()
        except:
            e = sys.exc_info()[0]
            print("exception " + str(e))
            self.notify('')


    def StartNotify(self):
        if self._notifying:
            print('Prop: Already notifying, nothing to do')
            return
        print('Start notifying')
        self._notifying = True


    def StopNotify(self):
        if not self._notifying:
            print('Prop: Not notifying, nothing to do')
            return
        print('Stop notifying')
        self._notifying = False


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

        self._notifying = False
        self._timeoutSourceId = None

    def notify(self, replyString):
        if not self._notifying:
            return
        reply = replyString.encode()
        if len(reply) % chunkLength == 0:
            reply.append(" ".encode()[0])
        while len(reply) > 0:
            subReply = reply[0:chunkLength]
            reply = reply[chunkLength:]
            self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    { 'Value': dbus.ByteArray(subReply) }, [])

    def getPunches(self):
        uri = URIPATH + 'punches/'
        req = requests.get(uri)
        thePunches = req.json()['Value']
        self.notify(thePunches)
        return True

    def StartNotify(self):
        if self._notifying:
            print('PunchesCharacteristic - Already notifying, stop first')
            self.StopNotify()
        print('PunchesCharacteristic - Start notifying')
        uri = URIPATH + 'sendtoblenoenabled/1/'
        req = requests.get(uri)
        self._notifying = True
        self._timeoutSourceId = GLib.timeout_add(1000, self.getPunches)

    def StopNotify(self):
        if not self._notifying:
            print('PunchesCharacteristic - Not notifying, nothing to do')
            return
        print('PunchesCharacteristic - Stop notifying')
        if self._timeoutSourceId != None:
            GLib.source_remove(self._timeoutSourceId)
            self._timeoutSourceId = None
        uri = URIPATH + 'sendtoblenoenabled/0/'
        req = requests.get(uri)
        self._notifying = False

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
        self._includeAllResponseByteArray = None

    def notify(self, replyString):
        if not self._notifying:
            print('TestPunches - notify - not notifying')
            return
        reply = replyString.encode()
        if len(reply) % chunkLength == 0:
            reply.append(" ".encode()[0])
        while len(reply) > 0:
            subReply = reply[0:chunkLength]
            reply = reply[chunkLength:]
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
            replyString = resp.text
            print("getTestPunches - replyString: " + replyString)
            self.notify(replyString)
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
            for k, v in options.items():
                print(k, v)
            #print('MTU: ' + str(options['mtu']))
            #print('Offset: ' + str(options['offset']))
            #no of test punches max 100, ie 3 chars
            #interval max 15000 ms, ie 5 chars
            #SI number currently max 7 digits
            #=> max 15 + 2 semicolon => 17 chars
            #No need to support long values since it will always be below 20
            noOfPunchesAndIntervalAndSINo = bytes(value).decode()
            print(noOfPunchesAndIntervalAndSINo)
            self._noOfPunchesToAdd = int(noOfPunchesAndIntervalAndSINo.split('\t')[0])
            self._noOfPunchesAdded = 0
            intervalMs = 1000
            if len(noOfPunchesAndIntervalAndSINo.split('\t')) > 1:
                intervalMs = int(noOfPunchesAndIntervalAndSINo.split('\t')[1])
            if len(noOfPunchesAndIntervalAndSINo.split('\t')) > 2:
                self._siNo = noOfPunchesAndIntervalAndSINo.split('\t')[2]

            if self._timeoutSourceIdAddPunches != None:
                GLib.source_remove(self._timeoutSourceIdAddPunches)
                self._timeoutSourceIdAddPunches = None

            print("Number of punches to add: " + str(self._noOfPunchesToAdd) + " interval: " + str(intervalMs) + " si number: " + self._siNo)
            self._testBatchGuid = uuid.uuid4()
            self._timeoutSourceIdAddPunches = GLib.timeout_add(1000, self.addTestPunch)
        except:
            print("exception")

    def ReadValue(self, options):
        print('TestPunchesCharacteristic - ReadValue')
        for k, v in options.items():
            print(k, v)
        #print('MTU: ' + str(options['mtu']))
        #print('Offset: ' + str(options['offset']))
        offset = options['offset']
        includeAll = True
        if offset == 0:
            uri = URIPATH + 'testpunches/gettestpunches/' + self._testBatchGuid + '/' + ("true" if includeAll else "false") + '/'
            resp = requests.get(uri)
            self._includeAllResponseByteArray = resp.json()['Value'].encode()
        return dbus.ByteArray(self._includeAllResponseByteArray[offset:])

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

        self.updateLocalName()
        #self.add_local_name('Test')
        self.include_tx_power = True
        #self.add_data(0x26, [0x01, 0x01, 0x00])

    def updateLocalName(self):
        uri = URIPATH + 'wirocdevicename/'
        print(uri)
        req = requests.get(uri)
        self.add_local_name(req.json()['Value'])

    def updateAdvertisement(self):
        global ad_manager
        ad_manager.UnregisterAdvertisement(self)
        ad_manager.RegisterAdvertisement(self.get_path(), {},
                                         reply_handler=register_ad_cb,
                                         error_handler=register_ad_error_cb)
        print("Reregister advertisment after local name update")


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
        if not adapter:
            print('GattManager1 interface not found')
            uri = URIPATH + 'startpatchap6212/'
            req = requests.get(uri)
            returnValue = 'startpatchap6212\t' + str(req.json()['Value'])
            print('returnValue ' + str(returnValue))
            if  str(req.json()['Value']) == 'OK':
                adapter = find_adapter(bus)
                if not adapter:
                    return

        global device
        device = find_device1(bus)

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
