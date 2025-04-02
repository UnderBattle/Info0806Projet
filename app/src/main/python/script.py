import paho.mqtt.client as mqtt
import json
import time

BROKER = "194.57.103.203"
PORT = 1883
TOPIC = "antenne"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)
client.loop_start()

def send_mqtt_message(message):
    json_message = json.dumps(message)
    client.publish(TOPIC, json_message)
    return json_message

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connexion au broker réussie")
        client.subscribe(TOPIC)
    else:
        print(f"Echec de connexion, code d'erreur: {rc}")

def on_publish(client, userdata, mid):
    print("Message publié avec succès")

def on_message(client, userdata, msg):
    last_message = msg.payload.decode()
    print(f"Message reçu : {last_message}")

def connect_mqtt():
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message
    return "Connexion MQTT tentée"

client.on_connect = on_connect
client.on_publish = on_publish
client.on_message = on_message