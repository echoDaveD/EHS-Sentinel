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
        time.sleep(1)
    
    def publish_message(self, name, value):
        """
        Publishes a message to the MQTT broker.
        Args:
            name (str): The name of the message to be published.
            value (Any): The value of the message to be published.
        Returns:
            None
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

           # if sensor_type == "sensor":
           #     value = json.dumps(f"{value}"})
        else:
            topicname = f"{self.topicPrefix.replace('/', '')}/{newname}"

        self._publish(topicname, value, qos=2, retain=True)

    def auto_discover_hass(self, topicname, nameraw, namenorm, sensor_type):

        device = {
            "identifiers": [self.DEVICE_ID],
            "name": "EHS-Sentinel",
            "manufacturer": "Samsung",
            "model": "EHS-Sentinel",
            "sw_version": "1.0.0"
        }

        entity = {
            "name": f"Samsung EHS - {namenorm}",
            "object_id": f"{self.DEVICE_ID}_{namenorm.lower()}",
            #"unique_id": f"{self.DEVICE_ID}_{nameraw.lower()}",
            "state_topic": f"{topicname}"
        }

        if sensor_type == "sensor":
            entity['value_template'] = "{{ value }}"
            if len(self.config.NASA_REPO[nameraw]['unit']) > 0:
                entity['unit_of_measurement'] = self.config.NASA_REPO[nameraw]['unit']
                match entity['unit_of_measurement']:
                    case '°C':
                        entity['device_class'] = "temperature"
                    case '%':
                        entity['device_class'] = "power_factor"
                    case 'kW':
                        entity['device_class'] = "power"
                    case 'rpm':
                        entity['device_class'] = "speed"
                    case 'kgf/cm2':
                        entity['device_class'] = "pressure"
                    case 'HP':
                        entity['device_class'] = "power"
                    case _:
                        entity['device_class'] = None

        else:
            entity['payload_on'] = "ON"
            entity['payload_off'] = "OFF"
        
        entity['device'] = device

        logger.debug(f"Auto Discovery HomeAssistant Message: ")
        logger.debug(f"{entity}")

        self._publish(f"{self.config.MQTT['homeAssistantAutoDiscoverTopic']}/{sensor_type}/{self.DEVICE_ID}/config",
                      json.dumps(entity),
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
