class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoMotorInitialized(Error):
    """Raised when no motor found"""
    print('Motor init failed')
