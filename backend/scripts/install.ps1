$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$VenvDir = if ($env:BUILDCLAW_VENV_DIR) { $env:BUILDCLAW_VENV_DIR } else { Join-Path $RootDir ".venv" }
$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }

function Require-Command {
    param([string]$CommandName)
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing dependency: $CommandName"
    }
}

Require-Command $PythonBin
Require-Command "git"

Set-Location $RootDir

if (-not (Test-Path $VenvDir)) {
    & $PythonBin -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e .

$ConfigPath = Join-Path $RootDir "config.yaml"
$ConfigExamplePath = Join-Path $RootDir "config.example.yaml"
if (-not (Test-Path $ConfigPath)) {
    Copy-Item $ConfigExamplePath $ConfigPath
    Write-Host "Created config.yaml from config.example.yaml"
}

$EnvPath = Join-Path $RootDir ".env"
$EnvExamplePath = Join-Path $RootDir ".env.example"
if ((-not (Test-Path $EnvPath)) -and (Test-Path $EnvExamplePath)) {
    Copy-Item $EnvExamplePath $EnvPath
    Write-Host "Created .env from .env.example"
}

& $VenvPython (Join-Path $RootDir "scripts\doctor.py")

Write-Host ""
Write-Host "BuildClaw backend installation completed."
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit backend\config.yaml"
Write-Host "2. Edit backend\.env if needed"
Write-Host "3. Start with:"
Write-Host "   backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080"
