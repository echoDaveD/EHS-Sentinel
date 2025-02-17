class EHSException(Exception):
    """Base class for exceptions in this module."""
    pass

class MessageWarningException(EHSException):
    """Exception raised by message errors.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, argument, message):
        self.argument = argument
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.argument}'

class ConfigException(EHSException):
    """Exception raised by multiple Config errors.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, argument, message="Config Parameter Exception: "):
        self.argument = argument
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.argument}'
    
class ArgumentException(EHSException):
    """Exception raised by multiple Arguments errors.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, argument, message="Argument is missing"):
        self.argument = argument
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.argument} -> {self.message}'
    
class SkipInvalidPacketException(EHSException):
    """Exception raised for invalid message types.

    Attributes:
        message_type -- input message type which caused the error
        message -- explanation of the error
    """

    def __init__(self, message="Invalid message type provided"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'