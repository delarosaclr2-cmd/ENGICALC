@echo off
REM Instala las dependencias de Calculadoras de Ingenieria RMR
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 python -m pip install -r requirements.txt
pause
