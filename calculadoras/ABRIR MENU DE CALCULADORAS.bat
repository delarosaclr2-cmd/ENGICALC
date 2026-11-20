@echo off
rem Doble clic para abrir el menu de las calculadoras
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
    echo No se encontro Python. Instalelo desde https://www.python.org/downloads/
    pause
    exit /b 1
)
%PY% -c "import openpyxl, reportlab" >nul 2>nul
if errorlevel 1 (
    echo Primera ejecucion: instalando componentes necesarios...
    %PY% -m pip install --user openpyxl reportlab
    if errorlevel 1 ( pause & exit /b 1 )
)
set "PYW=pythonw"
where pyw >nul 2>nul && set "PYW=pyw -3"
start "" %PYW% "%~dp0menu_calculadoras.pyw"
exit /b 0
