import argparse
import os
from EHSExceptions import ArgumentException

from CustomLogger import logger, setDebugMode

class EHSArguments:
    """
    EHSArguments is a singleton class that handles command-line arguments for the EHS Sentinel script.
    Attributes:
        CONFIGFILE (str): Path to the configuration file.
        DRYRUN (bool): Flag indicating if the script should run in dry run mode.
        DUMPFILE (str): Path to the dump file.
        _instance (EHSArguments): Singleton instance of the class.
    Methods:
        __new__(cls, *args, **kwargs): Ensures only one instance of the class is created.
        __init__(self): Initializes the class, parses command-line arguments, and sets attributes.
    """

    CONFIGFILE = ''
    DRYRUN = False
    DUMPFILE = ''

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Create and return a new instance of the class, ensuring that only one instance exists (singleton pattern).
        This method overrides the default behavior of object creation to implement the singleton pattern. 
        It checks if an instance of the class already exists; if not, it creates a new instance and marks it as uninitialized.
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            EHSArguments: The singleton instance of the EHSArguments class.
        """

        if not cls._instance:
            cls._instance = super(EHSArguments, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initializes the EHSArguments class, parses command-line arguments, and sets up configuration.
        This method performs the following steps:
        1. Checks if the class has already been initialized to prevent re-initialization.
        2. Sets up an argument parser to handle command-line arguments.
        3. Parses the command-line arguments and validates them.
        4. Checks if the specified config file and dump file exist.
        5. Sets the class attributes based on the parsed arguments.
        Raises:
            ArgumentException: If the required arguments are not provided or if the specified files do not exist.
        """
        if self._initialized:
            return
        self._initialized = True
        logger.debug("init EHSArguments")
        parser = argparse.ArgumentParser(description="Process some integers.")
        parser.add_argument('--configfile', type=str, required=True, help='Config file path')
        parser.add_argument('--dumpfile', type=str,  required=False, help='File Path for where the Dumpfile should be written to or read from if dryrun flag is set too.')
        parser.add_argument('--dryrun', action='store_true', default=False, required=False, help='Run the script in dry run mode, data will be read from DumpFile and not MQTT Message will be sent.')
        parser.add_argument('-v', '--verbose', action='store_true', default=False, required=False, help='Enable verbose mode')

        args = parser.parse_args()

        if args.verbose:
            setDebugMode()

        logger.debug(args)

        if args.dryrun:
            if args.dumpfile is None:
                raise ArgumentException(argument="--dumpfile")

        # Check if the config file exists
        if not os.path.isfile(args.configfile):
            raise ArgumentException(argument=args.configfile, message="Config File does not exist")

        # Check if the dump file exists if set
        if args.dumpfile:
            if not os.path.isfile(args.dumpfile):
                raise ArgumentException(argument=args.dumpfile, message="Dump File does not exist")
            
        self.CONFIGFILE = args.configfile
        self.DUMPFILE = args.dumpfile
        self.DRYRUN = args.dryrun


