from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found.", status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid credentials."):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists."):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


# ---------------------------------------------------------------------------
# Global exception handlers — registered in app factory
# ---------------------------------------------------------------------------


def _error_body(message: str) -> dict:
    return {"detail": message}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.message))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internal details in non-debug mode
        import structlog
        log = structlog.get_logger(__name__)
        log.exception("Unhandled error", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("An unexpected error occurred. Please try again later."),
        )
