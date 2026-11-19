@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === HVAC Industrial Engineering Calculator - instalacion ===
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo No se encontro Python. Instale Python 3.11-3.13 de python.org marcando "Add to PATH". & pause & exit /b 1)
if not exist .venv (
  echo Creando entorno virtual .venv ...
  %PY% -m venv .venv || (echo Error creando el entorno virtual & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Error instalando dependencias & pause & exit /b 1)
echo.
echo Ejecutando pruebas de validacion...
python -m pytest -q
echo.
echo Instalacion terminada. Use ejecutar_app.bat para abrir la aplicacion.
pause
