$env:LLM_PROVIDER="mock"
$env:OPENAI_COMPATIBLE_API_KEY=""
$env:OPENAI_COMPATIBLE_BASE_URL=""
$env:OPENAI_COMPATIBLE_MODEL=""

cd d:\qq\a3-2026-04-01-15-32\backend
uvicorn app.main:app --reload
