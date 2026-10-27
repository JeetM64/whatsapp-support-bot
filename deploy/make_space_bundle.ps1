$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundle = Join-Path $root ".tmp\space-bundle-upload"
if (Test-Path -LiteralPath $bundle) { throw "Bundle target already exists: $bundle. Move it aside before rebuilding." }
New-Item -ItemType Directory -Path $bundle -Force | Out-Null
foreach ($path in @("Dockerfile", ".dockerignore", "requirements.txt", "README.md", "src", "kb", "config", "frontend", "deploy\huggingface\README.md")) {
    $source = Join-Path $root $path
    if (-not (Test-Path -LiteralPath $source)) { throw "Required bundle input missing: $path" }
    $destination = Join-Path $bundle $path
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}
Copy-Item (Join-Path $bundle "deploy\huggingface\README.md") (Join-Path $bundle "README.md") -Force
Write-Host "Space bundle ready: $bundle"


