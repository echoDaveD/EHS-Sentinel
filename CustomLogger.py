import logging
import inspect 

class IndentFormatter(logging.Formatter):
    """
    A custom logging formatter that adds indentation based on the call stack depth
    and includes the function name in the log record.
    Attributes:
        baseline (int): The baseline stack depth when the formatter is initialized.
    Methods:
        __init__(fmt=None, datefmt=None):
            Initializes the IndentFormatter with optional format and date format.
        format(rec):
            Formats the specified record as text, adding indentation and function name.
    """
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }


    def __init__( self, fmt=None, datefmt=None ):
        """
        Initializes the CustomLogger instance.
        Args:
            fmt (str, optional): The format string for the log messages. Defaults to None.
            datefmt (str, optional): The format string for the date in log messages. Defaults to None.
        Attributes:
            baseline (int): The baseline stack depth when the logger is initialized.
        """
        logging.Formatter.__init__(self, fmt, datefmt)
        self.baseline = len(inspect.stack())

    def format( self, rec ):
        """
        Formats the log record by adding indentation and function name.
        This method customizes the log record by adding an indentation level
        based on the current stack depth and includes the name of the function
        from which the log call was made. It then uses the base Formatter class
        to format the record and returns the formatted string.
        Args:
            rec (logging.LogRecord): The log record to be formatted.
        Returns:
            str: The formatted log record string.
        """
        log_fmt = self.FORMATS.get(rec.levelno)
        formatter = logging.Formatter(log_fmt)

        stack = inspect.stack()
        rec.indent = '    '*(len(stack)-self.baseline-3)
        rec.function = stack[8][3]
        out = logging.Formatter.format(self, rec)
        del rec.indent; del rec.function
        return out
    
# The following code sets up a custom logger with indentation support.
# It creates a custom formatter, a logger instance, and a stream handler.
# The custom formatter is set to the handler, which is then added to the logger.
# Finally, the logging level is set to INFO.

formatter = IndentFormatter("%(asctime)s - (%(filename)30s:%(lineno)-3d) - [%(levelname)-7s]: %(indent)s%(message)s ")
logger = logging.getLogger('logger')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def setDebugMode():
    """
    Set the logging level to DEBUG and log a message indicating that debug mode is enabled.
    This function sets the logging level of the logger to DEBUG, which means that all messages
    at the DEBUG level and above will be logged. It also logs a debug message to indicate that
    debug mode has been activated.
    """
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug mode is on...")

def setSilent():
    """
    Sets the logger to silent mode, where only messages at the ERROR level or higher are displayed.
    If the current logging level is not 'DEBUG', this function will log an informational message
    indicating that silent mode is being activated and then set the logging level to ERROR.
    """
    print(logger.level)
    if logger.level != 10:
        logger.info("Silent Mode is turning on, only Messages at Level ERROR or higher are displyed")
        logger.setLevel(logging.ERROR)