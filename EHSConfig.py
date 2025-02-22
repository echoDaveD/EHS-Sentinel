from EHSExceptions import ConfigException
from EHSArguments import EHSArguments
import yaml
import os

from CustomLogger import logger

class EHSConfig():
    """
    Singleton class to handle the configuration for the EHS Sentinel application.
    This class reads configuration parameters from a YAML file and validates them.
    It ensures that only one instance of the configuration exists throughout the application.
    Attributes:
        MQTT (dict): Configuration parameters for MQTT.
        GENERAL (dict): General configuration parameters.
        SERIAL (dict): Configuration parameters for serial communication.
        NASA_REPO (dict): Configuration parameters for NASA repository.
    Methods:
        __new__(cls, *args, **kwargs): Ensures only one instance of the class is created.
        __init__(self, *args, **kwargs): Initializes the configuration by reading and validating the YAML file.
        validate(self): Validates the configuration parameters.
    """

    _instance = None
    MQTT = None
    GENERAL = None
    SERIAL = None
    NASA_REPO = None
    LOGGING = {}

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the EHSConfig class if one does not already exist.
        This method ensures that only one instance of the EHSConfig class is created
        (singleton pattern). If an instance already exists, it returns the existing instance.
        Args:
            cls: The class being instantiated.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            EHSConfig: The single instance of the EHSConfig class.
        """

        if not cls._instance:
            cls._instance = super(EHSConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        """
        Initialize the EHSConfig instance.
        This method initializes the EHSConfig instance by loading configuration
        settings from a YAML file specified in the EHSArguments. It ensures that
        the initialization process is only performed once by checking the 
        _initialized attribute. If the instance is already initialized, the method 
        returns immediately. Otherwise, it proceeds to load the configuration and 
        validate it.
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Attributes:
            args (EHSArguments): An instance of EHSArguments containing the 
                                 configuration file path.
            MQTT (dict): MQTT configuration settings loaded from the YAML file.
            GENERAL (dict): General configuration settings loaded from the YAML file.
            SERIAL (dict): Serial configuration settings loaded from the YAML file.
        """
        if self._initialized:
            return
        self._initialized = True
        super().__init__(*args, **kwargs)

        logger.debug("init EHSConfig")
        self.args = EHSArguments()

        with open(self.args.CONFIGFILE, mode='r') as file:
            config = yaml.safe_load(file)
            self.MQTT = config.get('mqtt')
            self.GENERAL = config.get('general')
            self.SERIAL = config.get('serial')
            if 'logging' in config:
                self.LOGGING = config.get('logging')
            else:
                self.LOGGING = {}
            logger.debug(f"Configuration loaded: {config}")

        self.validate()


    def validate(self):
        """
        Validates the configuration parameters for the EHS Sentinel application.
        This method checks the presence and validity of various configuration parameters
        such as NASA repository file, serial device, baudrate, MQTT broker URL, broker port,
        and MQTT credentials. It raises a ConfigException if any required parameter is missing
        or invalid. Additionally, it sets default values for optional parameters if they are not provided.
        Raises:
            ConfigException: If any required configuration parameter is missing or invalid.
        """
        if os.path.isfile(self.GENERAL['nasaRepositoryFile']):
             with open(self.GENERAL['nasaRepositoryFile'], mode='r') as file:
                self.NASA_REPO = yaml.safe_load(file)
        else:
            raise ConfigException(argument=self.GENERAL['nasaRepositoryFile'], message="NASA Respository File is missing")

        if 'protocolFile' not in self.GENERAL:
            self.GENERAL['protocolFile'] = None

        if 'device' not in self.SERIAL:
            raise ConfigException(argument=self.SERIAL['device'], message="serial device config parameter is missing")
        
        if 'baudrate' not in self.SERIAL:
            raise ConfigException(argument=self.SERIAL['baudrate'], message="serial baudrate config parameter is missing")
        
        if 'broker-url' not in self.MQTT:
            raise ConfigException(argument=self.MQTT['broker-url'], message="mqtt broker-url config parameter is missing")
        
        if 'broker-port' not in self.MQTT:
            raise ConfigException(argument=self.MQTT['broker-port'], message="mqtt broker-port parameter is missing")
        
        if 'homeAssistantAutoDiscoverTopic' not in self.MQTT:
           self.MQTT['homeAssistantAutoDiscoverTopic'] = ""

        if 'useCamelCaseTopicNames' not in self.MQTT:
           self.MQTT['useCamelCaseTopicNames'] = False
        
        if 'topicPrefix' not in self.MQTT:
            self.MQTT['topicPrefix'] = "ehsSentinel"

        if 'client-id' not in self.MQTT:
            self.MQTT['client-id'] = "ehsSentinel"
        
        if 'user' not in self.MQTT and 'password' in self.MQTT:
            raise ConfigException(argument=self.SERIAL['device'], message="mqtt user parameter is missing")
        
        if 'password' not in self.MQTT and 'user' in self.MQTT:
            raise ConfigException(argument=self.SERIAL['device'], message="mqtt password parameter is missing")
        
        if 'messageNotFound' not in self.LOGGING:
            self.LOGGING['messageNotFound'] = False

        if 'messageNotFound' not in self.LOGGING:
            self.LOGGING['messageNotFound'] = False

        if 'deviceAdded' not in self.LOGGING:
            self.LOGGING['deviceAdded'] = True

        if 'packetNotFromIndoorOutdoor' not in self.LOGGING:
            self.LOGGING['packetNotFromIndoorOutdoor'] = False

        if 'proccessedMessage' not in self.LOGGING:
            self.LOGGING['proccessedMessage'] = False

        logger.info(f"Logging Config: {self.LOGGING}")
        