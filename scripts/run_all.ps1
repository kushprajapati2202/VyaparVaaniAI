# Run both Backend and Frontend in separate jobs or terminal windows
$env:PYTHONPATH = "$PSScriptRoot\..\backend"
$env:Path = "$env:LOCALAPPDATA\Programs\nodejs;" + $env:Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting VyaparVaani AI (Multilingual Voice Operations) " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start_backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start_frontend.ps1"

Write-Host "Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "Swagger Docs: http://localhost:8000/docs" -ForegroundColor Green
