# Start VyaparVaani AI React Frontend
$env:Path = "$env:LOCALAPPDATA\Programs\nodejs;" + $env:Path
Set-Location "$PSScriptRoot\..\frontend"
Write-Host "Starting VyaparVaani AI Frontend on http://localhost:5173..." -ForegroundColor Cyan
npm run dev
