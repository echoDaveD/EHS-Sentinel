import paho.mqtt.client as mqtt
import time
import json

# Get the logger
from CustomLogger import logger

class MQTTClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MQTTClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, broker=None, port=None, client_id=None, topicPrefix=None, useHassFormat=None, username=None, password=None):
        if self._initialized:
            return
        self._initialized = True
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.topicPrefix = topicPrefix
        self.useHassFormat = useHassFormat
        if username and password:
            self.client.username_pw_set(username, password)
        self.client.connect(broker, port)
        self.initialized = True
        self.client.loop_start()
        self.known_topics = set()  # Set to keep track of known topics
        self.known_topics_topic = "known/topics"  # Dedicated topic for storing known topics

    def on_message(self, client, userdata, msg):
        if msg.topic == self.known_topics_topic:
            # Update the known topics set with the retained message
            self.known_topics = set(json.loads(msg.payload.decode()))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT with result code {rc}")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.info(f"Disconnected with result code {rc}")
        if rc != 0:
            logger.warning("Unexpected disconnection. Reconnecting...")
            while True:
                try:
                    self.client.reconnect()
                    break
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                    time.sleep(5)

    def _publish(self, topic, payload, qos=0, retain=False):
        self.client.publish(topic, payload, qos, retain)
    
    def publishMessage(self, name, value):
        name = f"{self.topicPrefix.replace('/', '')}/{self._normalize_name(name)}"
        if self.useHassFormat:
            pass
        else:
            self._publish(name, value, qos=1, retain=False)

    def _normalize_name(self, name):
        prefix_to_remove = ['ENUM_', 'LVAR_', 'NASA_', 'VAR_']
        # remove unnecessary prefixes of name
        for prefix in prefix_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        name_parts = name.split("_")
        tmpname = name_parts[0].lower()
        # construct new name in CamelCase
        for i in range(1, len(name_parts)):
            tmpname += name_parts[i].capitalize()

        return tmpname
