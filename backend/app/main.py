from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router


def envelope(data=None, error=None, ok=True):
    return {"ok": ok, "data": data, "error": error}


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


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=envelope(ok=False, data=None, error={"code": "SERVER_ERROR", "message": str(exc)}),
    )


app.include_router(router)
