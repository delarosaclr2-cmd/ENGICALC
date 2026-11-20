@echo off
rem Crea un ejecutable .exe de la calculadora: Lineas de aceite
rem Resultado: dist\Lineas_De_Aceite\Lineas_De_Aceite.exe (copie la carpeta completa para usarlo en otra PC)
setlocal
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>nul || set "PY=python"
echo Instalando PyInstaller y componentes...
%PY% -m pip install --user pyinstaller -r requirements.txt
if errorlevel 1 goto :error
%PY% -m PyInstaller --noconfirm --clean --windowed --name "Lineas_De_Aceite" --add-data "casos;casos" --add-data "linea_aceite\ui\recursos;linea_aceite\ui\recursos" --icon "linea_aceite\ui\recursos\rmr.ico" "ejecutar_linea_aceite.pyw"
if errorlevel 1 goto :error
echo.
echo Listo: dist\Lineas_De_Aceite\Lineas_De_Aceite.exe
pause
exit /b 0

:error
echo No se pudo crear el ejecutable.
pause
exit /b 1
