#!/usr/bin/python3

import os
import signal
import time
import traceback
import urllib.request
from bs4 import BeautifulSoup

#import paho.mqtt.publish as mqtt_publish
import paho.mqtt.client as mqtt_client

# external files/classes
import logger
import serviceReport
import settings

exitNow = False
motionHASSDeviceStatus = {}
motionHASSServiceStatus = -1

OFF = 0
ON  = 1
OFFLINE = -1
OK = 0
ERROR = -1


def signal_handler(_signal, frame):
    global exitNow

    print('You pressed Ctrl+C!')
    exitNow = True


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT Client connected successfully")
        client.subscribe([(settings.MQTT_TOPIC_HOMEASSISTANT_BEDIENING, 1), (settings.MQTT_TOPIC_CHECK, 1)])
    else:
        print(("ERROR: MQTT Client connected with result code %s " % str(rc)))


def on_message(client, userdata, msgJson):
    print(('ERROR: Received ' + msgJson.topic + ' in on_message function' + str(msgJson.payload)))


def on_message_homeassistant_bediening(client, userdata, msg):
    global motionHASSServiceStatus

    # print("on_message_homeassistant_bediening:" + msg.topic + " " + str(msg.payload))
    # print(msg.topic + " " + str(msg.payload))

    topc = msg.topic.split('/')
    deviceName = topc[2]

    if deviceName in motionHASSDeviceStatus:
        status = int(msg.payload)
        print("Bediening: " + msg.topic + " " + str(status))
        #Store current device status
        motionHASSDeviceStatus.update({deviceName: status})
        for motionServerIP in settings.motionDetectionURL:
            if deviceName in settings.motionDetectionURL[motionServerIP]:
                switchMotionDetection(motionServerIP, deviceName, status)
    elif deviceName == 'Actief-Motion':
        status = int(msg.payload)
        print("Bediening: " + msg.topic + " " + str(status))
        if status == 1:
            motionHASSServiceStatus = True
        else:
            motionHASSServiceStatus = False


def checkMotionDetectionStatus(motionServerIP, deviceName):
    cmndUrl = "%s/status" % (settings.motionDetectionURL[motionServerIP][deviceName])
    #print(cmndUrl)
    try:
        response = urllib.request.urlopen(cmndUrl)

        if response.getcode() == 200:
            parsed_html = BeautifulSoup(response.read(), "html.parser")
            sStatus = parsed_html.body.text[34:38]
            print('%s: %s' % (deviceName, sStatus))
            if sStatus == 'ACTI':
                status = ON #'ACTI'=ACTIVE
            else:
                status = OFF #'PAUS'=PAUSE

    except urllib.error.URLError:
        status = OFFLINE #Service offline
        #print('%s: offline' % deviceName)

    #print('%s: %s' % (deviceName, status))
    return status


def switchMotionDetection(motionServerIP, deviceName, status):
    if status:
        detectionCmnd = 'start'
    else:
        detectionCmnd = 'pause'
    cmndUrl = "%s/%s" % (settings.motionDetectionURL[motionServerIP][deviceName], detectionCmnd)
    print("->" + cmndUrl)
    try:
        response = urllib.request.urlopen(cmndUrl)
    except urllib.error.URLError:
        print('ERROR: Unable to reach %s' % deviceName)
        return ERROR

    if response.getcode() != 200:
        print('ERROR: Motion %s not updated' % deviceName)
        return ERROR
    else:
        return OK


def checkMotionServiceStatus(motionServerIP):
    status = os.system('sudo systemctl -H root@%s is-active --quiet motion' % motionServerIP)
    if status == 0:
        return ON
    else:
        return OFF


def switchMotionService(motionServerIP, status):
    if status:
        serviceCmnd = 'restart'
    else:
        serviceCmnd = 'stop'
    status = os.system('sudo systemctl -H root@%s %s --quiet motion' % (motionServerIP, serviceCmnd))
    if status != 0:
        print('ERROR: Unable to %s motion service on %s' % (serviceCmnd, motionServerIP))


###
# Initalisation ####
###
logger.initLogger(settings.LOG_FILENAME)

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Give Mosquitto and Home_logic the time to startup
time.sleep(1)

# First start the MQTT client
client = mqtt_client.Client()
client.message_callback_add(settings.MQTT_TOPIC_HOMEASSISTANT_BEDIENING, on_message_homeassistant_bediening)
client.message_callback_add(settings.MQTT_TOPIC_CHECK,     serviceReport.on_message_check)
client.on_connect = on_connect
client.on_message = on_message
client.connect(settings.MQTT_ServerIP, settings.MQTT_ServerPort, 60)
client.loop_start()

#Init motionHASSDeviceStatus
for motionServerIP in settings.motionDetectionURL:
    print("MotionServer: %s" % motionServerIP)

    for deviceName in settings.motionDetectionURL[motionServerIP]:
        print("deviceName: %s" % deviceName)
        motionHASSDeviceStatus[deviceName] = OFFLINE

while not exitNow:
    try:
        time.sleep(10)
        # for deviceName in settings.motionDetectionURL:
        #     checkMotionDetectionStatus(deviceName)

        for motionServerIP in settings.motionDetectionURL:
            #print("Check MotionServer: %s" % motionServerIP)

            for deviceName in settings.motionDetectionURL[motionServerIP]:
                status = checkMotionDetectionStatus(motionServerIP, deviceName)
                if status == OFFLINE:
                    if motionHASSServiceStatus:
                        print("Motion service not running on %s, start it" % motionServerIP)
                        time.sleep(3)
                        #Switch on motion service
                        switchMotionService(motionServerIP, ON)
                    #Break out of this loop, not necessary to check other devices
                    break
                else:
                    #Service is online
                    if not motionHASSServiceStatus:
                        print("Motion service is running on %s, stop it" % motionServerIP)
                        time.sleep(3)
                        #Switch on motion service
                        switchMotionService(motionServerIP, OFF)
                        #Break out of this loop, not necessary to check other devices
                        break
                    else:
                        #Motion service is running:
                        #   Check the current state against the settings and
                        #   switch on/off if the state is different
                        if status != motionHASSDeviceStatus[deviceName]:
                            if motionHASSDeviceStatus[deviceName] != OFFLINE:
                                # print("Status: %d != motionHASSDeviceStatus: %d" % (status, motionHASSDeviceStatus[deviceName]))
                                switchMotionDetection(motionServerIP, deviceName, motionHASSDeviceStatus[deviceName])

    # In case the message contains unusual data
    except urllib.error.URLError as arg:
        print(arg)
        traceback.print_exc()
        time.sleep(1)

    # Quit the program by Ctrl-C
    except KeyboardInterrupt:
        print("Program aborted by Ctrl-C")
        exit()

    # Handle other exceptions and print the error
    except Exception as arg:
        print("%s" % str(arg))
        traceback.print_exc()
        time.sleep(120)

#End of while loop
print("Clean exit!")
