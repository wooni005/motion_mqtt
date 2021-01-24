#!/usr/bin/python

MQTT_ServerIP     = "192.168.5.248"
MQTT_ServerPort   = 1883
LOG_FILENAME      = "/home/pi/log/motion_mqtt.log"

#Bediend door gebruiker:
MQTT_TOPIC_HOMEASSISTANT_BEDIENING = 'huis/HomeLogic/+/bediening'

motionDetectionURL = {
    "192.168.5.249": {
        "Actief-Motion-Binnenplaats":   "http://192.168.5.249:8090/1/detection",
        "Actief-Motion-Voortuin":       "http://192.168.5.249:8090/2/detection",
        # "Actief-Motion-Binnen":         "http://192.168.5.249:8090/3/detection",
    },
    "192.168.5.250": {
        # "Actief-Motion-Helling":        "http://192.168.5.250:8090/1/detection",
        "Actief-Motion-Brug":           "http://192.168.5.250:8090/2/detection",
    }
}

MQTT_TOPIC_CHECK     = "huis/MotionMQTT/RPiHome/check"
MQTT_TOPIC_REPORT    = "huis/MotionMQTT/RPiHome/report"
