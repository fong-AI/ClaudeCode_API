# run.ps1 — chạy Claude-as-API
# Dùng:  .\run.ps1            (chỉ local, an toàn)
#        .\run.ps1 -Expose    (mở ra LAN/tunnel: tắt Bash + bật token)

param([switch]$Expose)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$token = (Get-Content .\.token.txt -Raw).Trim()

if ($Expose) {
    $env:CLAUDE_TOOLS = "Read,Grep,Glob"   # tắt Bash khi mở ra ngoài
    $env:API_TOKEN    = $token
    Write-Host "=== CHE DO EXPOSE (an toan) ===" -ForegroundColor Yellow
    Write-Host "Token (gui kem header Authorization: Bearer ...):" -ForegroundColor Cyan
    Write-Host "  $token" -ForegroundColor Green
    Write-Host "Bash: TAT | Host: 0.0.0.0:8000"
    & .\.venv\Scripts\uvicorn.exe api:app --host 0.0.0.0 --port 8000
} else {
    Write-Host "=== CHE DO LOCAL ===" -ForegroundColor Yellow
    Write-Host "Chi PC nay goi duoc: http://localhost:8000"
    & .\.venv\Scripts\uvicorn.exe api:app --port 8000
}
