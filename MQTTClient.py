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
    MQTTClient is a singleton class that manages the connection and communication with an MQTT broker.
    It handles the initialization, connection, subscription, and message publishing for the MQTT client.
    The class also supports Home Assistant auto-discovery and maintains a list of known devices.
    """
    _instance = None
    STOP = asyncio.Event()

    DEVICE_ID = "samsung_ehssentinel"

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the class if one does not already exist.
        This method ensures that only one instance of the class is created (singleton pattern).
        If an instance already exists, it returns the existing instance.
        Otherwise, it creates a new instance, marks it as uninitialized, and returns it.
        Args:
            cls: The class being instantiated.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            An instance of the class.
        """
        
        if not cls._instance:
            cls._instance = super(MQTTClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initializes the MQTTClient instance.
        This constructor sets up the MQTT client with the necessary configuration
        parameters, including broker URL, port, client ID, and authentication credentials.
        It also assigns callback functions for various MQTT events such as connect, 
        disconnect, message, and subscribe. Additionally, it initializes topic-related 
        settings and a list to keep track of known topics.
        Attributes:
            config (EHSConfig): Configuration object for MQTT settings.
            args (EHSArguments): Argument parser object.
            broker (str): URL of the MQTT broker.
            port (int): Port number of the MQTT broker.
            client_id (str): Client ID for the MQTT connection.
            client (gmqtt.Client): MQTT client instance.
            topicPrefix (str): Prefix for MQTT topics.
            homeAssistantAutoDiscoverTopic (str): Topic for Home Assistant auto-discovery.
            useCamelCaseTopicNames (bool): Flag to use camel case for topic names.
            initialized (bool): Flag indicating if the client has been initialized.
            known_topics (list): List to keep track of known topics.
            known_devices_topic (str): Topic for storing known devices.
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
        This function logs the connection attempt, connects to the MQTT broker using the specified
        broker address and port, and sets the keepalive interval. If the CLEAN_KNOWN_DEVICES argument
        is set, it publishes an empty message to the known devices topic to clear it.
        Args:
            None
        Returns:
            None
        """
        
        logger.info("[MQTT] Connecting to broker...")
        await self.client.connect(self.broker, self.port, keepalive=60, version=gmqtt.constants.MQTTv311)

        if self.args.CLEAN_KNOWN_DEVICES:
            self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
            logger.info("Known Devices Topic have been cleared")

    def subscribe_known_topics(self):
        """
        Subscribe to predefined MQTT topics.
        This method subscribes the MQTT client to a set of known topics, which include:
        - A topic for known devices, constructed using the topic prefix and known devices topic.
        - A status topic for Home Assistant auto-discovery.
        The subscription is done with a QoS level of 1 for both topics.
        Logging:
        - Logs an info message indicating the subscription to known devices topic.
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
            properties (paho.mqtt.properties.Properties): The properties associated with the message.
        This function performs the following actions:
        - If the topic matches the known devices topic, it updates the known topics list with the retained message.
        - If the topic matches the Home Assistant auto-discover status topic, it logs the status message and, if the payload indicates that Home Assistant is online, it clears the known devices topic.
        """
        
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

    def on_connect(self, client, flags, rc, properties):
        """
        Callback function for when the client receives a CONNACK response from the server.
        Parameters:
        client (paho.mqtt.client.Client): The client instance for this callback.
        flags (dict): Response flags sent by the broker.
        rc (int): The connection result.
        properties (paho.mqtt.properties.Properties): The properties associated with the connection.
        If the connection is successful (rc == 0), logs a success message and subscribes to known topics if any.
        Otherwise, logs an error message with the return code.
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
        This function logs the disconnection event and attempts to reconnect the client
        in case of an unexpected disconnection. It will keep trying to reconnect every
        5 seconds until successful.
        Args:
            client (paho.mqtt.client.Client): The MQTT client instance that disconnected.
            packet (paho.mqtt.packet.Packet): The disconnect packet.
            exc (Exception, optional): The exception that caused the disconnection, if any.
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
        Publishes a message to a specified MQTT topic.
        Args:
            topic (str): The MQTT topic to publish to.
            payload (str): The message payload to publish.
            qos (int, optional): The Quality of Service level for the message. Defaults to 0.
            retain (bool, optional): If True, the message will be retained by the broker. Defaults to False.
        Returns:
            None
        """
        
        logger.debug(f"MQTT Publish Topic: {topic} payload: {payload}")
        self.client.publish(f"{topic}", payload, qos, retain)
        #time.sleep(0.1)

    def refresh_known_devices(self, devname):
        """
        Refreshes the list of known devices by publishing the current known topics to the MQTT broker.
        Args:
            devname (str): The name of the device to refresh.
        This function constructs a topic string by replacing '/' with an empty string in the topicPrefix,
        then concatenates it with the known_devices_topic. It publishes the known topics as a comma-separated
        string to this constructed topic with the retain flag set to True.
        """
        self.known_topics.append(devname)
        if self.config.LOGGING['deviceAdded']:
            logger.info(f"Device added no. {len(self.known_topics):<3}:  {devname} ")
        else:
            logger.debug(f"Device added no. {len(self.known_topics):<3}:  {devname} ")
        self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", ",".join(self.known_topics), retain=True)
    
    def publish_message(self, name, value):
        """
        Publishes a message to an MQTT topic.
        This function normalizes the given name, determines the appropriate MQTT topic,
        and publishes the provided value to that topic. It also handles Home Assistant
        auto-discovery if configured.
        Args:
            name (str): The name of the sensor or device.
            value (int, float, bool, str): The value to be published. If the value is a float,
                           it will be rounded to two decimal places.
        Raises:
            ValueError: If the value type is not supported for publishing.
        """
        
        newname = f"{self._normalize_name(name)}"
        
        if len(self.homeAssistantAutoDiscoverTopic) > 0:

            if name not in self.known_topics:
                self.auto_discover_hass(name)
                self.refresh_known_devices(name)

            sensor_type = "sensor"
            if 'enum' in self.config.NASA_REPO[name]:
                enum = [*self.config.NASA_REPO[name]['enum'].values()]
                if all([en.lower() in ['on', 'off'] for en in enum]):
                    sensor_type = "binary_sensor"
            topicname = f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{newname.lower()}/state"
        else:
            topicname = f"{self.topicPrefix.replace('/', '')}/{newname}"
        
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = round(value, 2) if isinstance(value, float) and "." in f"{value}" else value

        self._publish(topicname, value, qos=2, retain=False)

    def clear_hass(self):
        """
        clears all entities/components fpr the HomeAssistant Device
        """ 
        entities = {}
        for nasa in self.config.NASA_REPO:
            namenorm = self._normalize_name(nasa)
            sensor_type = self._get_sensor_type(nasa)
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
        """
        Automatically discovers and configures Home Assistant entities based on the NASA_REPO configuration.
        This function iterates through the NASA_REPO configuration to create and configure entities for Home Assistant.
        It determines the type of sensor (binary_sensor or sensor) based on the configuration and sets various attributes
        such as unit of measurement, device class, state class, and payloads for binary sensors. It then constructs a device
        configuration payload and publishes it to the Home Assistant MQTT discovery topic.
        The function performs the following steps:
        1. Iterates through the NASA_REPO configuration.
        2. Normalizes the name of each NASA_REPO entry.
        3. Determines the sensor type (binary_sensor or sensor) based on the 'enum' values.
        4. Configures the entity attributes such as unit of measurement, device class, state class, and payloads.
        5. Constructs a device configuration payload.
        6. Publishes the device configuration to the Home Assistant MQTT discovery topic.
        Attributes:
            entities (dict): A dictionary to store the configured entities.
            device (dict): A dictionary to store the device configuration payload.
        Logs:
            Logs the constructed device configuration payload for debugging purposes.
        Publishes:
            Publishes the device configuration payload to the Home Assistant MQTT discovery topic with QoS 2 and retain flag set to True.
        """
        entity = {}
        namenorm = self._normalize_name(name)
        sensor_type = self._get_sensor_type(name)
        entity = {
                "name": f"{namenorm}",""
                "object_id": f"{self.DEVICE_ID}_{namenorm.lower()}",
                "unique_id": f"{self.DEVICE_ID}_{name.lower()}",
                "platform": sensor_type,
                #"expire_after": 86400,  # 1 day (24h * 60m * 60s)
                "value_template": "{{ value }}",
                #"value_template": "{{ value if value | length > 0 else 'unavailable' }}",
                "state_topic": f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}_{namenorm.lower()}/state",
            }

        if sensor_type == "sensor":
            if len(self.config.NASA_REPO[name]['unit']) > 0:
                entity['unit_of_measurement'] = self.config.NASA_REPO[name]['unit']
                if entity['unit_of_measurement'] == "\u00b0C":
                    entity['device_class'] = "temperature"
                elif entity['unit_of_measurement'] == '%':
                    entity['state_class'] = "measurement"
                elif entity['unit_of_measurement'] == 'kW':
                    entity['device_class'] = "power"
                elif entity['unit_of_measurement'] == 'rpm':
                    entity['state_class'] = "measurement"
                elif entity['unit_of_measurement'] == 'bar':
                    entity['device_class'] = "pressure"
                elif entity['unit_of_measurement'] == 'HP':
                    entity['device_class'] = "power"
                elif entity['unit_of_measurement'] == 'hz':
                    entity['device_class'] = "frequency"
                else:
                    entity['device_class'] = None
        else:
            entity['payload_on'] = "ON"
            entity['payload_off'] = "OFF"

        if 'state_class' in self.config.NASA_REPO[name]:
            entity['state_class'] = self.config.NASA_REPO[name]['state_class']
        
        if 'device_class' in self.config.NASA_REPO[name]:
            entity['device_class'] = self.config.NASA_REPO[name]['device_class']

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
    
    def _get_sensor_type(self, name):
        """
        return the sensor type of given measurement
        Args:
            name (str): The name of the measurement.
        Returns:
            str: The sensor type: sensor or binary_sensor.
        """
        sensor_type = "sensor"
        if 'enum' in self.config.NASA_REPO[name]:
            enum = [*self.config.NASA_REPO[name]['enum'].values()]
            if all([en.lower() in ['on', 'off'] for en in enum]):
                sensor_type = "binary_sensor"

        return sensor_type
