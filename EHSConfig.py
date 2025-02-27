from EHSExceptions import ConfigException
from EHSArguments import EHSArguments
import yaml
import os
import re

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
    TCP = None
    NASA_REPO = None
    LOGGING = {}
    POLLING = None

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

            if 'tcp' in config:
                self.TCP = config.get('tcp')

            if 'serial' in config:
                self.SERIAL = config.get('serial')

            if 'logging' in config:
                self.LOGGING = config.get('logging')
            else:
                self.LOGGING = {}

            if 'polling' in config:
                self.POLLING = config.get('polling')

            logger.debug(f"Configuration loaded: {config}")
            

        self.validate()
    
    def parse_time_string(self, time_str: str) -> int:
        """
        Parses a time string like '10m' or '10s' and converts it to seconds.
        
        Supported formats:
        - '10m' for 10 minutes
        - '10s' for 10 seconds
        
        Returns:
        - Equivalent time in seconds as an integer.
        """
        match = re.match(r'^(\d+)([smh])$', time_str.strip(), re.IGNORECASE)
        if not match:
            raise ValueError("Invalid time format. Use '10s', '10m', or '10h'.")
        
        value, unit = int(match.group(1)), match.group(2).lower()
        
        conversion_factors = {
            's': 1,   # seconds
            'm': 60,  # minutes
            'h': 3600 # hours
        }
    
        return value * conversion_factors[unit]

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

        if self.SERIAL is None and self.TCP is None:
            raise ConfigException(argument="", message="define tcp or serial config parms")

        if self.SERIAL is not None and self.TCP is not None:
            raise ConfigException(argument="", message="you cannot define tcp and serial please define only one")

        if self.SERIAL is not None:
            if 'device' not in self.SERIAL:
                raise ConfigException(argument=self.SERIAL['device'], message="serial device config parameter is missing")
            
            if 'baudrate' not in self.SERIAL:
                raise ConfigException(argument=self.SERIAL['baudrate'], message="serial baudrate config parameter is missing")
            
        if self.TCP is not None:
            if 'ip' not in self.TCP:
                raise ConfigException(argument=self.TCP['ip'], message="tcp ip config parameter is missing")
            
            if 'port' not in self.TCP:
                raise ConfigException(argument=self.TCP['port'], message="tcp port config parameter is missing")
            
        if self.POLLING is not None:
            if 'fetch_interval' not in self.POLLING:
                raise ConfigException(argument='', message="fetch_interval in polling parameter is missing")
            
            if 'groups' not in self.POLLING:
                raise ConfigException(argument='', message="groups in polling parameter is missing")
            
            if 'fetch_interval' in self.POLLING and 'groups' in self.POLLING:
                for poller in self.POLLING['fetch_interval']:
                    if poller['name'] not in self.POLLING['groups']:
                        raise ConfigException(argument=poller['name'], message="Groupname from fetch_interval not defined in groups: ")
                    if 'schedule' in poller:
                        try:
                            poller['schedule'] = self.parse_time_string(poller['schedule'])
                        except ValueError as e:
                            raise ConfigException(argument=poller['schedule'], message="schedule value from fetch_interval couldn't be validated, use format 10s, 10m or 10h")
                
                for group in self.POLLING['groups']:
                    for ele in self.POLLING['groups'][group]:
                        if ele not in self.NASA_REPO:
                            raise ConfigException(argument=ele, message="Element from group not in NASA Repository")
             
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

        if 'pollerMessage' not in self.LOGGING:
            self.LOGGING['pollerMessage'] = False

        logger.info(f"Logging Config:")
        for key, value in self.LOGGING.items():
            logger.info(f"    {key}: {value}")
        