@echo off
rem Crea un ejecutable .exe de la calculadora: Gas combustible
rem Resultado: dist\Gas_Combustible\Gas_Combustible.exe (copie la carpeta completa para usarlo en otra PC)
setlocal
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>nul || set "PY=python"
echo Instalando PyInstaller y componentes...
%PY% -m pip install --user pyinstaller -r requirements.txt
if errorlevel 1 goto :error
%PY% -m PyInstaller --noconfirm --clean --windowed --name "Gas_Combustible" --add-data "casos;casos" --add-data "gas_combustible\ui\recursos;gas_combustible\ui\recursos" --icon "gas_combustible\ui\recursos\rmr.ico" "ejecutar_gas_combustible.pyw"
if errorlevel 1 goto :error
echo.
echo Listo: dist\Gas_Combustible\Gas_Combustible.exe
pause
exit /b 0

:error
echo No se pudo crear el ejecutable.
pause
exit /b 1
