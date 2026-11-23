@echo off
rem Doble clic para abrir la calculadora: Lineas de gas y aire comprimido
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY goto :sinpython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 goto :sinpython
%PY% -c "import openpyxl, reportlab" >nul 2>nul
if errorlevel 1 (
    echo Primera ejecucion: instalando componentes necesarios...
    %PY% -m pip install --user -r requirements.txt
    if errorlevel 1 goto :errorpip
)
set "PYW=pythonw"
where pyw >nul 2>nul && set "PYW=pyw -3"
start "" %PYW% "%~dp0ejecutar_linea_gas.pyw"
exit /b 0

:sinpython
echo No se encontro Python 3.9 o mas reciente.
echo Instalelo desde https://www.python.org/downloads/ y marque "Add python.exe to PATH".
pause
exit /b 1

:errorpip
echo No se pudieron instalar los componentes. Revise su conexion a internet
echo o ejecute manualmente:  py -m pip install -r requirements.txt
pause
exit /b 1
