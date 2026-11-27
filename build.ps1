# Construye dist\AguacatePomodoro.exe
# Uso (en PowerShell, desde la carpeta del proyecto):  .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1

Write-Host "1/4 Instalando dependencias..." -ForegroundColor Green
pip install -q -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "No se han podido instalar las dependencias" }

Write-Host "2/4 Pasando los tests..." -ForegroundColor Green
python -m unittest -q
if ($LASTEXITCODE -ne 0) { throw "Los tests han fallado: no construyo el .exe" }

Write-Host "3/4 Generando el icono..." -ForegroundColor Green
python tools\make_icon.py build\aguacate.ico

Write-Host "4/4 Empaquetando con PyInstaller (tarda 1-2 minutos)..." -ForegroundColor Green
pyinstaller --noconfirm --clean --onefile --windowed `
    --name AguacatePomodoro `
    --icon build\aguacate.ico `
    --exclude-module PySide6.QtMultimedia `
    --exclude-module PySide6.QtNetwork `
    --exclude-module PySide6.QtQml `
    --exclude-module PySide6.QtQuick `
    --exclude-module tkinter `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller ha fallado" }

$exe = Get-Item dist\AguacatePomodoro.exe
Write-Host ("Listo: {0} ({1:N0} MB)" -f $exe.FullName, ($exe.Length / 1MB)) -ForegroundColor Green
