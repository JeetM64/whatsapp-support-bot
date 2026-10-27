$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Project venv is missing. Create it with py -3.12 -m venv .venv and install requirements.txt." }
$env:PYTHONUTF8 = "1"
if (Test-Path -LiteralPath (Join-Path $projectRoot "model_cache")) {
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
}
$env:ENV = "demo"
if (-not $env:AGENT_API_KEY) {
    $env:AGENT_API_KEY = "demo-agent-key-change-me"
    Write-Host "Demo agent key (local demo only): $env:AGENT_API_KEY"
}

Write-Host "Building the knowledge base..."
& $python -m src.kb build
if ($LASTEXITCODE -ne 0) { throw "Knowledge base build failed." }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "model_cache\fastembed"))) {
    Write-Host "Warming the multilingual retrieval model..."
    & $python -m src.rag warmup
    if ($LASTEXITCODE -ne 0) { throw "Model warmup failed. Check model_cache and HF_HUB_OFFLINE." }
}
& $python -m src.app seed-demo
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed." }

$listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    throw "Port 8000 is occupied by PID $($listener.OwningProcess) ($($owner.ProcessName)); stop that process and rerun this script."
}
Write-Host "Chat:    http://127.0.0.1:8000/"
Write-Host "Agent:   http://127.0.0.1:8000/agent"
Write-Host "Founder: http://127.0.0.1:8000/founder"

& $python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
