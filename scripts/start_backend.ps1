# Start VyaparVaani AI FastAPI Backend
$env:PYTHONPATH = "$PSScriptRoot\..\backend"
Set-Location "$PSScriptRoot\..\backend"
Write-Host "Starting VyaparVaani AI Backend on http://localhost:8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
