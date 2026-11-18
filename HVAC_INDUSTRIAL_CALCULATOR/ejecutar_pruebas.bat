@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m pytest -v
echo.
echo Registro de pruebas: tests\results\registro_pruebas.md
pause
