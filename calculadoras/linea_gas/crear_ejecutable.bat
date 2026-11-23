@echo off
rem Crea un ejecutable .exe de la calculadora: Lineas de gas y aire comprimido
rem Resultado: dist\Lineas_De_Gas_Y_Aire\Lineas_De_Gas_Y_Aire.exe (copie la carpeta completa para usarlo en otra PC)
setlocal
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>nul || set "PY=python"
echo Instalando PyInstaller y componentes...
%PY% -m pip install --user pyinstaller -r requirements.txt
if errorlevel 1 goto :error
%PY% -m PyInstaller --noconfirm --clean --windowed --name "Lineas_De_Gas_Y_Aire" --add-data "casos;casos" --add-data "linea_gas\ui\recursos;linea_gas\ui\recursos" --icon "linea_gas\ui\recursos\rmr.ico" "ejecutar_linea_gas.pyw"
if errorlevel 1 goto :error
echo.
echo Listo: dist\Lineas_De_Gas_Y_Aire\Lineas_De_Gas_Y_Aire.exe
pause
exit /b 0

:error
echo No se pudo crear el ejecutable.
pause
exit /b 1
