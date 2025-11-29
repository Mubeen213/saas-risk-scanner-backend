class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=401)


class AuthorizationException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=403)


class NotFoundException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=404)


class ValidationException(AppException):
    def __init__(self, code: str, message: str, details: list | None = None):
        super().__init__(code, message, status_code=400)
        self.details = details or []
