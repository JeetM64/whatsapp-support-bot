$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:PYTHONUTF8 = "1"
if (Test-Path -LiteralPath (Join-Path $projectRoot "model_cache")) {
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
}

& (Join-Path $projectRoot ".venv\Scripts\python.exe") -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
