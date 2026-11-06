class ApiError(Exception):
    def __init__(self, status, message, details=None):
        self.status, self.message, self.details = status, message, details
