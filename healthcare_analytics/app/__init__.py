"""Healthcare Analytics and Patient Risk Indicator System (educational, synthetic data only)."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import default_database_url, parse_api_keys
from .constants import DISCLAIMER
from .db import get_engine
from .errors import ApiError

STATIC = Path(__file__).parent / "static"


def create_app(test_config=None) -> FastAPI:
    cfg = {"DATABASE_URL": default_database_url(),
           "API_KEYS": parse_api_keys(os.environ.get("API_KEYS", ""))}
    if test_config:
        cfg.update(test_config)

    app = FastAPI(title="Healthcare Analytics and Patient Risk Indicator System",
                  description=DISCLAIMER, version="1.0")
    app.state.engine = get_engine(cfg["DATABASE_URL"])
    app.state.api_keys = cfg["API_KEYS"]

    @app.exception_handler(ApiError)
    async def api_error(_: Request, err: ApiError):
        body = {"error": err.message}
        if err.details:
            body["details"] = err.details
        return JSONResponse(body, status_code=err.status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, err: StarletteHTTPException):
        return JSONResponse({"error": err.detail}, status_code=err.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, err: RequestValidationError):
        details = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in err.errors()]
        return JSONResponse({"error": "Invalid request", "details": details}, status_code=422)

    from .routes import router
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/dashboard")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC / "dashboard.html")

    return app
