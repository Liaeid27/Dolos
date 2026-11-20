@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0Heimnetz.ps1"
if errorlevel 1 (
  echo Diese Einrichtung als Administrator im privaten Heimnetz starten.
  pause
  exit /b 1
)
python -X utf8 importieren.py --apply --power
if errorlevel 1 (
  echo.
  echo Bei "Zugriff verweigert" diese Datei per Rechtsklick als Administrator ausfuehren.
  pause
  exit /b 1
)
pause
