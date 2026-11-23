from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.schemas import ApiErrorBody

STATUS = {
    "IMAGE_NOT_FOUND": 404, "SESSION_NOT_FOUND": 404, "NOT_PRECOMPUTED": 404,
    "INVALID_PARAM": 422, "MODE_REQUIRES_MULTISPECTRAL": 422, "TIF_NOT_13_BANDS": 422,
    "EXPRESSION_PARSE_ERROR": 422, "SHAPE_MISMATCH": 422, "LIVE_LIMIT_EXCEEDED": 413,
    "FORMAT_NOT_SUPPORTED": 422, "UPLOAD_TOO_LARGE": 413, "UNSUPPORTED_FILE": 415,
    "INTERNAL_ERROR": 500,
}
RESPONSES = {status: {"model": ApiErrorBody} for status in set(STATUS.values())}


class ApiError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code = code
        self.details = details


def install_handlers(app):
    @app.exception_handler(ApiError)
    async def contract_error(request: Request, exc: ApiError):
        return JSONResponse({"error": {"code": exc.code, "message": str(exc), "details": exc.details}},
                            status_code=STATUS[exc.code])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [".".join(map(str, item["loc"])) for item in exc.errors()]
        return await contract_error(request, ApiError("INVALID_PARAM", "Parameter tidak valid.", fields=fields))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = "IMAGE_NOT_FOUND" if exc.status_code == 404 else "INVALID_PARAM"
        return JSONResponse({"error": {"code": code, "message": "Permintaan tidak dapat diproses.",
                                       "details": {}}}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return await contract_error(request, ApiError("INTERNAL_ERROR", "Terjadi galat internal."))
