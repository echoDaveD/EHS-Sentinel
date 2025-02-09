import paho.mqtt.client as mqtt
import time
import json
import asyncio

# Get the logger
from CustomLogger import logger
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig

class MQTTClient:
    _instance = None

    DEVICE_ID = "samsung_ehssentinel"

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the MQTTClient class if one does not already exist.
        This method ensures that only one instance of the MQTTClient class is created
        (Singleton pattern). If an instance already exists, it returns the existing instance.
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
        Initializes the MQTTClient instance.
        This method sets up the MQTT client with the configuration provided by the EHSConfig and EHSArguments classes.
        It ensures that the client is only initialized once, sets up the MQTT broker connection, and starts the client loop.
        Attributes:
            config (EHSConfig): Configuration object for the MQTT client.
            args (EHSArguments): Arguments object for the MQTT client.
            broker (str): URL of the MQTT broker.
            port (int): Port of the MQTT broker.
            client_id (str): Client ID for the MQTT client.
            client (mqtt.Client): MQTT client instance.
            topicPrefix (str): Prefix for MQTT topics.
            homeAssistantAutoDiscoverTopic (str): Topic for Home Assistant auto-discovery.
            useCamelCaseTopicNames (bool): Flag to use camel case for topic names.
            known_topics (set): Set to keep track of known topics.
            known_topics_topic (str): Dedicated topic for storing known topics.
        Raises:
            Exception: If the MQTT client fails to connect to the broker.
        """

        if self._initialized:
            return
        self.config = EHSConfig()
        self.args = EHSArguments()
        self._initialized = True
        self.broker = self.config.MQTT['broker-url']
        self.port = self.config.MQTT['broker-port']
        self.client_id = self.config.MQTT['client-id']
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.topicPrefix = self.config.MQTT['topicPrefix']
        self.homeAssistantAutoDiscoverTopic = self.config.MQTT['homeAssistantAutoDiscoverTopic']
        self.useCamelCaseTopicNames = self.config.MQTT['useCamelCaseTopicNames']
        if self.config.MQTT['user'] and self.config.MQTT['password']:
            self.client.username_pw_set(self.config.MQTT['user'], self.config.MQTT['password'])
        self.client.connect(self.broker, self.port)
        self.initialized = True
        self.client.loop_start()
        self.known_topics: list = list()  # Set to keep track of known topics
        self.known_devices_topic = "known/devices"  # Dedicated topic for storing known topics

        if self.args.CLEAN_KNOWN_DEVICES:
            self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", " ", retain=True)
            logger.info("Known Devices Topic have been cleared")

    def subscribe_known_topics(self):
        """
        Subscribe to the known topics topic to receive updates on known topics.
        This method subscribes to the `known_devices_topic` to keep track of known topics.
        Returns:
            None
        """
        logger.info("Subscribe to known devices topic")
        self.client.subscribe(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", qos=1)

    def subscribe_hass_status_topics(self):
        """
        Subscribes to the Home Assistant status topic to react to birth messages.
        This method subscribes the MQTT client to the Home Assistant status topic
        with a Quality of Service (QoS) level of 1. It logs an informational message
        indicating that the subscription has been made.
        The subscription allows the client to react to birth messages from Home Assistant,
        which are used to signal the start of Home Assistant.
        Returns:
            None
        """
        
        logger.info("Subscribe to HASS Status Topic to react on birthmessages")
        self.client.subscribe(f"{self.homeAssistantAutoDiscoverTopic}/status", qos=1)

    def on_message(self, client, userdata, msg):
        """
        Callback function that is called when a message is received from the MQTT broker.
        Args:
            client (paho.mqtt.client.Client): The client instance for this callback.
            userdata (any): The private user data as set in Client() or userdata_set().
            msg (paho.mqtt.client.MQTTMessage): An instance of MQTTMessage, which contains the topic and payload.
        This function updates the known topics set with the retained message if the message topic matches the known topics topic.
        """

        if self.known_devices_topic in msg.topic:
            # Update the known devices set with the retained message
            self.known_topics = msg.payload.decode().split(",")

        logger.info(f"HASS Status Messages {msg.topic} received: {msg.payload.decode()}")
        #if f"{self.homeAssistantAutoDiscoverTopic}/status" in msg.topic:
            

    def refresh_known_devices(self, devname):
        self._publish(f"{self.topicPrefix.replace('/', '')}/{self.known_devices_topic}", ",".join(self.known_topics), retain=True)

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback function for when the client receives a CONNACK response from the server.
        Args:
            client (paho.mqtt.client.Client): The client instance for this callback.
            userdata (any): The private user data as set in Client() or userdata_set().
            flags (dict): Response flags sent by the broker.
            rc (int): The connection result.
        Returns:
            None
        Logs:
            - Info: When the connection is successful (rc == 0).
            - Error: When the connection fails (rc != 0).
        """

        if rc == 0:
            logger.info(f"Connected to MQTT with result code {rc}")
            if len(self.homeAssistantAutoDiscoverTopic) > 0:
                self.subscribe_known_topics()
                self.subscribe_hass_status_topics()
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        """
        Callback function that is called when the client disconnects from the MQTT broker.
        Args:
            client (paho.mqtt.client.Client): The client instance for this callback.
            userdata (Any): The private user data as set in Client() or userdata_set().
            rc (int): The disconnection result code. A value of 0 indicates a clean disconnection.
        Logs:
            - Info level log indicating the disconnection result code.
            - Warning level log if the disconnection was unexpected.
            - Error level log if reconnection attempts fail.
        Behavior:
            - If the disconnection was unexpected (rc != 0), it attempts to reconnect indefinitely.
            - Logs reconnection attempts and errors, and waits for 5 seconds before retrying.
        """

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
        """
        Publish a message to a specified MQTT topic.
        Args:
            topic (str): The MQTT topic to publish to.
            payload (str): The message payload to send.
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
        This method constructs the appropriate MQTT topic based on the provided
        name and value, and then publishes the value to that topic. If Home Assistant
        auto-discovery is enabled, it will also handle the auto-discovery configuration.
        Args:
            name (str): The name of the sensor or device.
            value (int, float, bool): The value to be published. If the value is a float,
                                      it will be rounded to 2 decimal places.
        Raises:
            ValueError: If the value is not of type int, float, or bool.
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

        self._publish(topicname, value, qos=2, retain=True)

    def auto_discover_hass(self, topicname, nameraw, namenorm, sensor_type):
        """
        Automatically discovers and configures a Home Assistant entity for the given sensor or switch.
        Args:
            topicname (str): The MQTT topic name.
            nameraw (str): The raw name of the sensor or switch.
            namenorm (str): The normalized name of the sensor or switch.
            sensor_type (str): The type of the sensor or switch (e.g., "sensor", "switch").
        Returns:
            None
        This function creates a Home Assistant discovery message for the specified sensor or switch,
        including its configuration and device information. It publishes the configuration to the
        MQTT broker and updates the list of known topics and devices.
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
                    entity[namenorm]['device_class'] = "power_factor"
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
