class AppException(Exception):
    """Base exception — all business-rule errors inherit from this."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required."):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class AuthorizationError(AppException):
    def __init__(self, message: str = "You don't have permission to access this resource."):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found.", status_code=404, error_code="NOT_FOUND")


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR")


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409, error_code="CONFLICT")


class ExternalServiceError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=502, error_code="EXTERNAL_SERVICE_ERROR")


class OptimizationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="OPTIMIZATION_ERROR")
