#!/usr/bin/python

import paho.mqtt.publish as mqtt_publish
import json

# external files/classes
import settings

# System check
ACTION_NOTHING = 0
ACTION_RESTART = 1

checkMsg = 'OK'
checkFail = False
checkAction = ACTION_NOTHING
checkReport = {}


# Called by mqtt
def on_message_check(client, userdata, msgJson):
    # print("on_message_check: "+msgJson.topic+": "+str(msgJson.payload))
    sendCheckReportToHomeLogic(checkFail, checkAction, checkMsg)


# Send the report to the Home Logic system checker
def sendCheckReportToHomeLogic(fail, action, msg):
    global checkMsg
    global checkFail

    checkMsg = msg
    checkFail = fail
    checkReport['checkFail'] = checkFail
    checkReport['checkAction'] = checkAction
    checkReport['checkMsg'] = checkMsg
    mqtt_publish.single(settings.MQTT_TOPIC_REPORT, json.dumps(checkReport), qos=1, hostname=settings.MQTT_ServerIP)


# Don't wait for the Home Logic system checker, report it directly
def sendFailureToHomeLogic(_checkAction, _checkMsg):
    sendCheckReportToHomeLogic(True, _checkAction, _checkMsg)
