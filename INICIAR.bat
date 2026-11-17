@echo off
REM Abre el menu principal de Calculadoras de Ingenieria RMR
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 menu_principal.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw menu_principal.py & exit /b)
python menu_principal.py
if errorlevel 1 pause
