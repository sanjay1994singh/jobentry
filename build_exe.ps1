$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Project virtualenv not found. Create it first with python -m venv .venv and install requirements."
}

& $VenvPython -m pip install -r requirements.txt
& $VenvPython manage.py check
& $VenvPython manage.py migrate
& $VenvPython manage.py collectstatic --noinput
& $VenvPython -m PyInstaller packaging\harinam_paper.spec --clean --noconfirm

Write-Host ""
Write-Host "Ready EXE:"
Write-Host (Join-Path $ProjectRoot "dist\HarinamPaper.exe")
