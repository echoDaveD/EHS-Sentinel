import asyncio
import os
import signal
import json
import time

import gmqtt

# Get the logger
from CustomLogger import logger
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from MessageProducer import MessageProducer

class MQTTClient:
    """
    MQTTClient is a singleton class that manages the connection and communication with an MQTT broker.
    It handles the initialization, connection, subscription, and message publishing for the MQTT client.
    The class also supports Home Assistant auto-discovery and maintains a list of known devices.
    """
    _instance = None
    STOP = asyncio.Event()

    DEVICE_ID = "samsung_ehssentinel"

    def __new__(cls, *args, **kwargs):
        
        if not cls._instance:
            cls._instance = super(MQTTClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        
        if self._initialized:
            return
        self.config = EHSConfig()
        self.args = EHSArguments()
        self.message_producer = None
        self._initialized = True
        self.broker = self.config.MQTT['broker-url']
        self.port = self.config.MQTT['broker-port']
        self.client_id = self.config.MQTT['client-id']
        self.client = gmqtt.Client(self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        if self.config.MQTT['user'] and self.config.MQTT['password']:
            self.client.set_auth_credentials(self.config.MQTT['user'], self.config.MQTT['password'])
        self.topicPrefix = self.config.MQTT['topicPrefix']
        self.homeAssistantAutoDiscoverTopic = self.config.MQTT['homeAssistantAutoDiscoverTopic']
        self.useCamelCaseTopicNames = self.config.MQTT['useCamelCaseTopicNames']

        self.initialized = True
        self.known_topics: list = list()  # Set to keep track of known topics
        self.known_devices_topic = "known/devices"  # Dedicated topic for storing known topics

    async def connect(self):
        logger.info("[MQTT] Connecting to broker...")
        await self.client.connect(self.broker, self.port, keepalive=60, version=gmqtt.constants.MQTTv311)

        if self.args.CLEAN_KNOWN_DEVICES:
            self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
            logger.info("Known Devices Topic have been cleared")

    def subscribe_known_topics(self):        
        logger.info("Subscribe to known devices topic")
        sublist =  [
                gmqtt.Subscription(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", 1),
                gmqtt.Subscription(f"{self.homeAssistantAutoDiscoverTopic}/status", 1)
            ]
        if self.config.GENERAL['allowControl']:
            sublist.append(gmqtt.Subscription(f"{self.topicPrefix.replace('/', '')}/entity/+/set", 1))

        self.client.subscribe(sublist)

    def on_subscribe(self, client, mid, qos, properties):
        logger.debug('SUBSCRIBED')

    def on_message(self, client, topic, payload, qos, properties):        
        if self.known_devices_topic in topic:
            # Update the known devices set with the retained message
            self.known_topics = list(filter(None, [x.strip() for x in payload.decode().split(",")]))
            if properties['retain'] == True:
                if self.config.LOGGING['deviceAdded']:
                    logger.info(f"Loaded devices from known devices Topic:")

                    for idx, devname in enumerate(self.known_topics, start=1):
                        logger.info(f"Device no. {idx:<3}:  {devname} ")
                else:
                    logger.debug(f"Loaded devices from known devices Topic:")
                    for idx, devname in enumerate(self.known_topics):
                        logger.debug(f"Device added no. {idx:<3}:  {devname} ")

        if f"{self.homeAssistantAutoDiscoverTopic}/status" == topic:
            logger.info(f"HASS Status Messages {topic} received: {payload.decode()}")
            if payload.decode() == "online":
                self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
                logger.info("Known Devices Topic have been cleared")          
                self.clear_hass()
                logger.info("All configuration from HASS has been resetet") 
        
        if topic.startswith(f"{self.topicPrefix.replace('/', '')}/entity"):
            logger.info(f"HASS Set Entity Messages {topic} received: {payload.decode()}")
            parts = topic.split("/")
            if self.message_producer is None:
                self.message_producer = MessageProducer(None)
            asyncio.create_task(self.message_producer.write_request(parts[2], payload.decode(), read_request_after=True))

    def on_connect(self, client, flags, rc, properties):
        if rc == 0:
            logger.info(f"Connected to MQTT with result code {rc}")
            if len(self.homeAssistantAutoDiscoverTopic) > 0:
                self.subscribe_known_topics()
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, packet, exc=None):        
        logger.info(f"Disconnected with result code ")
        logger.warning("Unexpected disconnection. Reconnecting...")
        while True:
            try:
                self.client.reconnect()
                break
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                time.sleep(5)

    def _publish(self, topic, payload, qos=0, retain=False):        
        logger.debug(f"MQTT Publish Topic: {topic} payload: {payload}")
        self.client.publish(f"{topic}", payload, qos, retain)
        #time.sleep(0.1)

    def refresh_known_devices(self, devname):
        self.known_topics.append(devname)
        if self.config.LOGGING['deviceAdded']:
            logger.info(f"Device added no. {len(self.known_topics):<3}:  {devname} ")
        else:
            logger.debug(f"Device added no. {len(self.known_topics):<3}:  {devname} ")
        self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", ",".join(self.known_topics), retain=True)
    
    async def publish_message(self, name, value):        
        newname = f"{self._normalize_name(name)}"
        
        if len(self.homeAssistantAutoDiscoverTopic) > 0:

            if name not in self.known_topics:
                self.auto_discover_hass(name)
                self.refresh_known_devices(name)

            if self.config.NASA_REPO[name]['hass_opts']['writable']:
                sensor_type = self.config.NASA_REPO[name]['hass_opts']['platform']['type']
            else:
                sensor_type = self.config.NASA_REPO[name]['hass_opts']['default_platform']
            topicname = f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{newname.lower()}/state"
        else:
            topicname = f"{self.topicPrefix.replace('/', '')}/{newname}"
        
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = round(value, 2) if isinstance(value, float) and "." in f"{value}" else value

        self._publish(topicname, value, qos=2, retain=False)

    def clear_hass(self):
        entities = {}
        for nasa in self.config.NASA_REPO:
            namenorm = self._normalize_name(nasa)
            if self.config.NASA_REPO[nasa]['hass_opts']['writable']:
                sensor_type = self.config.NASA_REPO[nasa]['hass_opts']['platform']['type']
            else:
                sensor_type = self.config.NASA_REPO[nasa]['hass_opts']['default_platform']
            entities[namenorm] = {"platform": sensor_type}
        
        device = {
            "device": self._get_device(),
            "origin": self._get_origin(),
            "components": entities,
            "qos": 2
        }

        logger.debug(f"Auto Discovery HomeAssistant Clear Message: ")
        logger.debug(f"{device}")

        self._publish(f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/device/{self.DEVICE_ID}/config",
                      json.dumps(device, ensure_ascii=False),
                      qos=2, 
                      retain=True)

    def auto_discover_hass(self, name):
        entity = {}
        namenorm = self._normalize_name(name)
        entity = {
                "name": f"{namenorm}",
                "object_id": f"{self.DEVICE_ID}_{namenorm.lower()}",
                "unique_id": f"{self.DEVICE_ID}_{name.lower()}",
                "force_update": True,
                #"expire_after": 86400,  # 1 day (24h * 60m * 60s)
                "value_template": "{{ value }}"
                #"value_template": "{{ value if value | length > 0 else 'unavailable' }}",
            }
        if self.config.NASA_REPO[name]['hass_opts']['writable'] and self.config.GENERAL['allowControl']:
            sensor_type = self.config.NASA_REPO[name]['hass_opts']['platform']['type']
            if sensor_type == 'select':
                entity['options'] = self.config.NASA_REPO[name]['hass_opts']['platform']['options']
            if sensor_type == 'number':
                entity['mode'] = self.config.NASA_REPO[name]['hass_opts']['platform']['mode']
                entity['min'] = self.config.NASA_REPO[name]['hass_opts']['platform']['min']
                entity['max'] = self.config.NASA_REPO[name]['hass_opts']['platform']['max']
                if 'step' in self.config.NASA_REPO[name]['hass_opts']['platform']:
                    entity['step'] = self.config.NASA_REPO[name]['hass_opts']['platform']['step']
                    
            entity['command_topic'] = f"{self.topicPrefix.replace('/', '')}/entity/{name}/set"
            entity['optimistic'] = False
        else:
            sensor_type = self.config.NASA_REPO[name]['hass_opts']['default_platform']

        if 'unit' in self.config.NASA_REPO[name]['hass_opts']:
            entity['unit_of_measurement'] = self.config.NASA_REPO[name]['hass_opts']['unit']

        entity['platform'] = sensor_type
        entity['state_topic'] = f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{namenorm.lower()}/state"

        if 'payload_off' in self.config.NASA_REPO[name]['hass_opts']['platform']:
            entity['payload_off'] = "OFF"
        if 'payload_on' in self.config.NASA_REPO[name]['hass_opts']['platform']:
            entity['payload_on'] = "ON"
        if 'state_class' in self.config.NASA_REPO[name]['hass_opts']:
            entity['state_class'] = self.config.NASA_REPO[name]['hass_opts']['state_class']
        if 'device_class' in self.config.NASA_REPO[name]['hass_opts']:
            entity['device_class'] = self.config.NASA_REPO[name]['hass_opts']['device_class']

        device = {
            "device": self._get_device(),
            "origin": self._get_origin(),
            "qos": 2
        }
        device.update(entity)

        logger.debug(f"Auto Discovery HomeAssistant Message: ")
        logger.debug(f"{device}")

        self._publish(f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{name.lower()}/config",
                      json.dumps(device, ensure_ascii=False),
                      qos=2, 
                      retain=True)

    def _get_device(self):
        return {
                "identifiers": self.DEVICE_ID,
                "name": "Samsung EHS",
                "manufacturer": "Samsung",
                "model": "Mono HQ Quiet",
                "sw_version": "1.0.0"
            }   

    def _get_origin(self):
        return {
                "name": "EHS-Sentinel",
                "support_url": "https://github.com/echoDaveD/EHS-Sentinel"
            }     

    def _normalize_name(self, name):
        if self.useCamelCaseTopicNames:
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
        else:
            tmpname = name

        return tmpname
