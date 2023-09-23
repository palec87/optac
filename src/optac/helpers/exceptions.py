class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoMotorInitialized(Error):
    """Raised when no motor found"""
    pass


class BoardInitFailed(Error):
    """Raised when board init fails"""
    pass


class MotorInitFailed(Error):
    """Raised when motor init fails"""
    pass

class FallingBackException(Error):

    def __init__(self, message=None):
        self.message = message
        super().__init__(self.message)
