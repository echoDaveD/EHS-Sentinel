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

class MQTTClient:
    """
    MQTTClient is a singleton class that manages the connection to an MQTT broker and handles
    publishing and subscribing to topics. It is designed to work with Home Assistant for
    auto-discovery of devices and sensors.

    Attributes:
        _instance (MQTTClient): The single instance of the MQTTClient class.
        STOP (asyncio.Event): Event to signal stopping the MQTT client.
        DEVICE_ID (str): The device ID used for MQTT topics.
        config (EHSConfig): Configuration object for the MQTT client.
        args (EHSArguments): Arguments object for the MQTT client.
        broker (str): URL of the MQTT broker.
        port (int): Port of the MQTT broker.
        client_id (str): Client ID for the MQTT client.
        client (gmqtt.Client): MQTT client instance.
        topicPrefix (str): Prefix for MQTT topics.
        homeAssistantAutoDiscoverTopic (str): Topic for Home Assistant auto-discovery.
        useCamelCaseTopicNames (bool): Flag to use camel case for topic names.
        known_topics (list): List to keep track of known topics.
        known_devices_topic (str): Dedicated topic for storing known topics.
    """
    _instance = None
    STOP = asyncio.Event()

    DEVICE_ID = "samsung_ehssentinel"

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the MQTTClient class if one does not already exist.
        This method ensures that the MQTTClient class follows the Singleton design pattern,
        meaning only one instance of the class can exist at any given time. If an instance
        already exists, it returns the existing instance. Otherwise, it creates a new instance
        and sets the _initialized attribute to False.
        Args:
            cls (type): The class being instantiated.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            MQTTClient: The single instance of the MQTTClient class.
        """
        
        if not cls._instance:
            cls._instance = super(MQTTClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize the MQTTClient instance.
        This constructor initializes the MQTT client with the configuration
        provided by the EHSConfig and EHSArguments classes. It sets up the
        MQTT broker connection details, client ID, and authentication credentials
        if provided. It also assigns callback functions for various MQTT events
        such as connect, disconnect, message, and subscribe. Additionally, it
        initializes the topic prefix, Home Assistant auto-discover topic, and
        topic naming convention.
        Attributes:
            config (EHSConfig): Configuration object for the MQTT client.
            args (EHSArguments): Argument parser object for the MQTT client.
            broker (str): URL of the MQTT broker.
            port (int): Port number of the MQTT broker.
            client_id (str): Client ID for the MQTT connection.
            client (gmqtt.Client): gmqtt client instance.
            topicPrefix (str): Prefix for MQTT topics.
            homeAssistantAutoDiscoverTopic (str): Topic for Home Assistant auto-discovery.
            useCamelCaseTopicNames (bool): Flag to use camel case for topic names.
            known_topics (list): List to keep track of known topics.
            known_devices_topic (str): Dedicated topic for storing known topics.
        """
        
        if self._initialized:
            return
        self.config = EHSConfig()
        self.args = EHSArguments()
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
        """
        Asynchronously connects to the MQTT broker and optionally clears the known devices topic.
        This method logs the connection attempt, connects to the MQTT broker using the specified
        broker address and port, and sets the keepalive interval. If the CLEAN_KNOWN_DEVICES
        argument is set to True, it publishes an empty message to the known devices topic to clear it.
        Args:
            None
        Returns:
            None
        Raises:
            Any exceptions raised by the underlying MQTT client library during connection.
        """

        logger.info("[MQTT] Connecting to broker...")
        await self.client.connect(self.broker, self.port, keepalive=60, version=gmqtt.constants.MQTTv311)

        if self.args.CLEAN_KNOWN_DEVICES:
            self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
            logger.info("Known Devices Topic have been cleared")

    def subscribe_known_topics(self):
        """
        Subscribes the MQTT client to known topics.
        This method subscribes the MQTT client to two specific topics:
        1. A topic for known devices, constructed using the topic prefix and known devices topic.
        2. A status topic for Home Assistant auto-discovery.
        The subscription QoS (Quality of Service) level for both topics is set to 1.
        Logging:
            Logs an informational message indicating that the client is subscribing to known devices topic.
        Raises:
            Any exceptions raised by the gmqtt.Subscription or self.client.subscribe methods.
        """
        
        logger.info("Subscribe to known devices topic")
        self.client.subscribe(
            [
                gmqtt.Subscription(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", 1),
                gmqtt.Subscription(f"{self.homeAssistantAutoDiscoverTopic}/status", 1)
            ]
        )

    def on_subscribe(self, client, mid, qos, properties):
        """
        Callback function that is called when the client subscribes to a topic.
        Args:
            client (paho.mqtt.client.Client): The client instance for this callback.
            mid (int): The message ID for the subscribe request.
            qos (int): The Quality of Service level for the subscription.
            properties (paho.mqtt.properties.Properties): The properties associated with the subscription.
        Returns:
            None
        """

        logger.debug('SUBSCRIBED')

    def on_message(self, client, topic, payload, qos, properties):
        """
        Callback function that is triggered when a message is received on a subscribed topic.
        Args:
            client (paho.mqtt.client.Client): The MQTT client instance.
            topic (str): The topic that the message was received on.
            payload (bytes): The message payload.
            qos (int): The quality of service level of the message.
            properties (paho.mqtt.properties.Properties): The properties of the message.
        Behavior:
            - If the topic matches the known devices topic, updates the known devices set with the retained message.
            - If the topic matches the Home Assistant auto-discover status topic, logs the status message and clears the known devices topic.
        """
        
        if self.known_devices_topic in topic:
            # Update the known devices set with the retained message
            self.known_topics = list(filter(None, [x.strip() for x in payload.decode().split(",")]))

        
        if f"{self.homeAssistantAutoDiscoverTopic}/status" == topic:
            logger.info(f"HASS Status Messages {topic} received: {payload.decode()}")
            self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
            logger.info("Known Devices Topic have been cleared")            

    def refresh_known_devices(self, devname):
        """
        Refreshes the list of known devices by publishing the updated list to the MQTT topic.
        Args:
            devname (str): The name of the device to be refreshed.
        Returns:
            None
        """

        self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", ",".join(self.known_topics), retain=True)

    def on_connect(self, client, flags, rc, properties):
        """
        Callback function for when the client receives a CONNACK response from the server.
        Args:
            client (paho.mqtt.client.Client): The client instance for this callback.
            flags (dict): Response flags sent by the broker.
            rc (int): The connection result.
            properties (paho.mqtt.properties.Properties): The properties associated with the connection.
        Returns:
            None
        Logs:
            - Info: When connected successfully with result code 0.
            - Error: When failed to connect with a non-zero result code.
        """
        
        if rc == 0:
            logger.info(f"Connected to MQTT with result code {rc}")
            if len(self.homeAssistantAutoDiscoverTopic) > 0:
                self.subscribe_known_topics()
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, packet, exc=None):
        """
        Callback function that is called when the client disconnects from the MQTT broker.
        Args:
            client (paho.mqtt.client.Client): The MQTT client instance that disconnected.
            packet (paho.mqtt.client.MQTTMessage): The MQTT message packet received during disconnection.
            exc (Exception, optional): The exception that caused the disconnection, if any. Defaults to None.
        Logs:
            Logs an info message indicating disconnection.
            Logs a warning message indicating an unexpected disconnection and attempts to reconnect.
            Logs an error message if reconnection fails and retries every 5 seconds.
        """
        
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
        """
        Publish a message to a specified MQTT topic.
        Args:
            topic (str): The MQTT topic to publish to.
            payload (str): The message payload to publish.
            qos (int, optional): The Quality of Service level for message delivery. Defaults to 0.
            retain (bool, optional): If True, the message will be retained by the broker. Defaults to False.
        Returns:
            None
        """
        
        logger.debug(f"MQTT Publish Topic: {topic} payload: {payload}")
        self.client.publish(f"{topic}", payload, qos, retain)
        #time.sleep(0.1)
    
    def publish_message(self, name, value):
        """
        Publishes a message to an MQTT topic.
        This method normalizes the given name, determines the appropriate MQTT topic,
        and publishes the provided value to that topic. If Home Assistant auto-discovery
        is enabled, it will also handle the auto-discovery configuration.
        Args:
            name (str): The name of the sensor or device.
            value (int, float, bool, str): The value to be published. If the value is a float,
                                           it will be rounded to two decimal places.
        Raises:
            KeyError: If the name is not found in the NASA_REPO configuration.
        """
        
        newname = f"{self._normalize_name(name)}"
        
        if len(self.homeAssistantAutoDiscoverTopic) > 0:
            sensor_type = "sensor"
            if 'enum' in self.config.NASA_REPO[name]:
                enum = [*self.config.NASA_REPO[name]['enum'].values()]
                if all([en.lower() in ['on', 'off'] for en in enum]):
                    sensor_type = "binary_sensor"
            topicname = f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{newname.lower()}/state"
            if name not in self.known_topics:
                self.auto_discover_hass(topicname, name, newname, sensor_type)

        else:
            topicname = f"{self.topicPrefix.replace('/', '')}/{newname}"
        
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = round(value, 2) if isinstance(value, float) and "." in f"{value}" else value

        self._publish(topicname, value, qos=2, retain=False)

    def auto_discover_hass(self, topicname, nameraw, namenorm, sensor_type):
        """
        Automatically discovers and configures Home Assistant entities for the MQTT client.
        This function creates and publishes a configuration payload for Home Assistant's MQTT discovery.
        It supports both sensor and binary sensor types, and sets appropriate attributes based on the 
        provided sensor type and unit of measurement.
        Args:
            topicname (str): The MQTT topic name.
            nameraw (str): The raw name of the sensor.
            namenorm (str): The normalized name of the sensor.
            sensor_type (str): The type of the sensor (e.g., "sensor" or "binary_sensor").
        Returns:
            None
        """
        
        entity = { namenorm: {
                "name": f"{namenorm}",
                "object_id": f"{self.DEVICE_ID}_{namenorm.lower()}",
                "unique_id": f"{self.DEVICE_ID}_{nameraw.lower()}",
                "platform": sensor_type,
                "value_template": "{{ value }}",
                "state_topic": f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{namenorm.lower()}/state",
            }
        }

        if sensor_type == "sensor":
            if len(self.config.NASA_REPO[nameraw]['unit']) > 0:
                entity[namenorm]['unit_of_measurement'] = self.config.NASA_REPO[nameraw]['unit']
                if entity[namenorm]['unit_of_measurement'] == "\u00b0C":
                    entity[namenorm]['device_class'] = "temperature"
                elif entity[namenorm]['unit_of_measurement'] == '%':
                    entity[namenorm]['state_class'] = "measurement"
                elif entity[namenorm]['unit_of_measurement'] == 'kW':
                    entity[namenorm]['device_class'] = "power"
                elif entity[namenorm]['unit_of_measurement'] == 'rpm':
                    entity[namenorm]['state_class'] = "measurement"
                elif entity[namenorm]['unit_of_measurement'] == 'bar':
                    entity[namenorm]['device_class'] = "pressure"
                elif entity[namenorm]['unit_of_measurement'] == 'HP':
                    entity[namenorm]['device_class'] = "power"
                elif entity[namenorm]['unit_of_measurement'] == 'hz':
                    entity[namenorm]['device_class'] = "frequency"
                else:
                        entity[namenorm]['device_class'] = None
        else:
            entity[namenorm]['payload_on'] = "ON"
            entity[namenorm]['payload_off'] = "OFF"

        if 'state_class' in self.config.NASA_REPO[nameraw]:
            entity[namenorm]['state_class'] = self.config.NASA_REPO[nameraw]['state_class']
        
        if 'device_class' in self.config.NASA_REPO[nameraw]:
            entity[namenorm]['device_class'] = self.config.NASA_REPO[nameraw]['device_class']


        device = {
            "device": {
                "identifiers": self.DEVICE_ID,
                "name": "Samsung EHS",
                "manufacturer": "Samsung",
                "model": "Mono HQ Quiet",
                "sw_version": "1.0.0"
            },
            "origin": {
                "name": "EHS-Sentinel",
                "support_url": "https://github.com/echoDaveD/EHS-Sentinel"
            },
            "components": entity,
            "qos": 2
        }

        logger.debug(f"Auto Discovery HomeAssistant Message: ")
        logger.debug(f"{device}")

        self._publish(f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/device/{self.DEVICE_ID}/config",
                      json.dumps(device, ensure_ascii=False),
                      qos=2, 
                      retain=True)

        self.known_topics.append(nameraw)
        self.refresh_known_devices(nameraw)


    def _normalize_name(self, name):
        """
        Normalize the given name based on the specified naming convention.
        If `useCamelCaseTopicNames` is True, the function will:
        - Remove any of the following prefixes from the name: 'ENUM_', 'LVAR_', 'NASA_', 'VAR_'.
        - Convert the name to CamelCase format.
        If `useCamelCaseTopicNames` is False, the function will return the name as is.
        Args:
            name (str): The name to be normalized.
        Returns:
            str: The normalized name.
        """

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
