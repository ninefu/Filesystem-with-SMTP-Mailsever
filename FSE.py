class FileSystemException(Exception):
    def __init__(self, errortype):
        self.parameter = errortype

    def __str__(self):
        return repr(self.parameter)
