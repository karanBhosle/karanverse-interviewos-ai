from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: object | None = None):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details})
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: object | None = None):
        super().__init__(404, "not_found", message, details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not own this resource"):
        super().__init__(403, "forbidden", message)


class ConflictError(AppError):
    def __init__(self, message: str, details: object | None = None):
        super().__init__(409, "conflict", message, details)


class ValidationAppError(AppError):
    def __init__(self, message: str, details: object | None = None):
        super().__init__(422, "validation_error", message, details)


class ProviderUnavailableError(AppError):
    def __init__(self, message: str = "The language model provider is unavailable"):
        super().__init__(503, "provider_unavailable", message)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.detail)
