from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AgentServiceException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PaymentException(AgentServiceException):
    def __init__(self, message: str):
        super().__init__(message, status_code=402)


class KodosumyException(AgentServiceException):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class MasumiException(AgentServiceException):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


async def agent_service_exception_handler(request: Request, exc: AgentServiceException):
    logger.error(
        "Agent service exception",
        error=exc.message,
        status_code=exc.status_code,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )