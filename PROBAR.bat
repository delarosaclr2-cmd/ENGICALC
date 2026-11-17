@echo off
REM Ejecuta las pruebas automaticas
cd /d "%~dp0"
py -3 -m pytest -v
if errorlevel 9009 python -m pytest -v
pause
