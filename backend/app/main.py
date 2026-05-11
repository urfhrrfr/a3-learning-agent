import os
from pathlib import Path


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if key not in os.environ:
                    os.environ[key] = os.path.expandvars(value.strip())


# Load .env files BEFORE any other imports. Prefer backend/.env but keep app/.env compatible.
backend_root = Path(__file__).resolve().parents[1]
load_env_file(backend_root / ".env")
load_env_file(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import state
from .routes import router


def envelope(data=None, error=None, ok=True):
    return {"ok": ok, "data": data, "error": error}


def error_code_for(status_code: int, detail: str) -> str:
    if status_code == 404 and "job" in detail:
        return "JOB_NOT_FOUND"
    if status_code == 404 and "resource" in detail:
        return "RESOURCE_NOT_FOUND"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 400:
        return "BAD_REQUEST"
    return "HTTP_ERROR"


app = FastAPI(title="A3 Personalized Learning Multi-Agent System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=envelope(
            ok=False,
            data=None,
            error={"code": "VALIDATION_ERROR", "message": "请求参数错误", "details": exc.errors()},
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(
            ok=False,
            data=None,
            error={"code": error_code_for(exc.status_code, detail), "message": detail, "details": {}},
        ),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=envelope(ok=False, data=None, error={"code": "SERVER_ERROR", "message": str(exc)}),
    )


app.include_router(router)

state.hydrate_from_db()
