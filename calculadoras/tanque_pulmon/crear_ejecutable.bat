@echo off
rem Crea un ejecutable .exe de la calculadora: Tanque pulmon de aire comprimido
rem Resultado: dist\Tanque_Pulmon\Tanque_Pulmon.exe (copie la carpeta completa para usarlo en otra PC)
setlocal
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>nul || set "PY=python"
echo Instalando PyInstaller y componentes...
%PY% -m pip install --user pyinstaller -r requirements.txt
if errorlevel 1 goto :error
%PY% -m PyInstaller --noconfirm --clean --windowed --name "Tanque_Pulmon" --add-data "casos;casos" --add-data "tanque_pulmon\ui\recursos;tanque_pulmon\ui\recursos" --icon "tanque_pulmon\ui\recursos\rmr.ico" "ejecutar_tanque_pulmon.pyw"
if errorlevel 1 goto :error
echo.
echo Listo: dist\Tanque_Pulmon\Tanque_Pulmon.exe
pause
exit /b 0

:error
echo No se pudo crear el ejecutable.
pause
exit /b 1
