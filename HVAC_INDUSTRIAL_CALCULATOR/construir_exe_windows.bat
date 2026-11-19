@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
pip show pyinstaller >nul 2>nul || pip install pyinstaller
pyinstaller --noconfirm --clean hvac_calculator.spec
echo.
echo Ejecutable generado en dist\HVAC_Calculator\HVAC_Calculator.exe
pause
