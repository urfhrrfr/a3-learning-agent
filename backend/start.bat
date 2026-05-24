@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set LLM_PROVIDER=mock
set OPENAI_COMPATIBLE_API_KEY=
set OPENAI_COMPATIBLE_BASE_URL=
set OPENAI_COMPATIBLE_MODEL=

cd /d D:\qq\a3-2026-04-01-15-32\backend
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="MYSQL_URL" set "MYSQL_URL=%%B"
    if /i "%%A"=="REDIS_URL" set "REDIS_URL=%%B"
  )
)
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) else (
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
)
