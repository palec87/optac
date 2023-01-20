class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoMotorInitialized(Error):
    """Raised when no motor found"""
    print('Initilize motor first')


class MotorInitFailed(Error):
    """Raised when no motor found"""
    print('Failure with init motor')
