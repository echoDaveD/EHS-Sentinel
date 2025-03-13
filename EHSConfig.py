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
    """

    _instance = None
    MQTT = None
    GENERAL = None
    SERIAL = None
    TCP = None
    NASA_REPO = None
    LOGGING = {}
    POLLING = None
    NASA_VAL_STORE = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EHSConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
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
        if os.path.isfile(self.GENERAL['nasaRepositoryFile']):
             with open(self.GENERAL['nasaRepositoryFile'], mode='r') as file:
                self.NASA_REPO = yaml.safe_load(file)
        else:
            raise ConfigException(argument=self.GENERAL['nasaRepositoryFile'], message="NASA Respository File is missing")

        if 'protocolFile' not in self.GENERAL:
            self.GENERAL['protocolFile'] = None

        if 'allowControl' not in self.GENERAL:
            self.GENERAL['allowControl'] = False

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

        if 'invalidPacket' not in self.LOGGING:
            self.LOGGING['invalidPacket'] = False

        if 'deviceAdded' not in self.LOGGING:
            self.LOGGING['deviceAdded'] = True

        if 'packetNotFromIndoorOutdoor' not in self.LOGGING:
            self.LOGGING['packetNotFromIndoorOutdoor'] = False

        if 'proccessedMessage' not in self.LOGGING:
            self.LOGGING['proccessedMessage'] = False

        if 'pollerMessage' not in self.LOGGING:
            self.LOGGING['pollerMessage'] = False

        if 'controlMessage' not in self.LOGGING:
            self.LOGGING['controlMessage'] = False

        logger.info(f"Logging Config:")
        for key, value in self.LOGGING.items():
            logger.info(f"    {key}: {value}")
        