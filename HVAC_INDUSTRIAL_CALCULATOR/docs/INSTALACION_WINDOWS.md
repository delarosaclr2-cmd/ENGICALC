# Instalación en Windows

## Requisitos

- Windows 10 u 11 de 64 bits.
- Python 3.11, 3.12 o 3.13 de 64 bits (https://www.python.org/downloads/windows/). Durante la instalación marque
  **"Add python.exe to PATH"**.
- Unos 600 MB libres (dependencias científicas y Qt).

## Opción A: con los scripts incluidos (recomendada)

1. Descomprima el ZIP en una ruta sin caracteres especiales, por ejemplo `C:\HVAC_INDUSTRIAL_CALCULATOR`.
2. Ejecute **`instalar_windows.bat`**. El script:
   - comprueba que Python esté disponible;
   - crea el entorno virtual `.venv`;
   - instala `requirements.txt`;
   - ejecuta las pruebas para confirmar que la instalación calcula correctamente.
3. Ejecute **`ejecutar_app.bat`** para abrir la aplicación.
4. Opcional: **`verificar_instalacion.bat`** calcula el banco de pruebas sin interfaz y genera una memoria PDF de
   verificación (muestra densidad, punto de diseño, punto de operación y dictamen).
5. Opcional: ejecute **`ejecutar_pruebas.bat`** cuando quiera repetir la validación (deja el registro en
   `tests\results\`).

## Opción B: manual (PowerShell o CMD)

```bat
cd C:\HVAC_INDUSTRIAL_CALCULATOR
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Ejecutable independiente (.exe)

En la misma máquina Windows con el entorno instalado:

```bat
construir_exe_windows.bat
```

El resultado queda en `dist\HVAC_Calculator\HVAC_Calculator.exe`. Esa carpeta contiene todo lo necesario y puede
copiarse a otra PC sin instalar Python. La configuración y las ediciones de la base de datos de cada usuario se
guardan en `%APPDATA%\HVAC_Industrial_Calculator`.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `python no se reconoce` | Reinstale Python marcando *Add to PATH* o use `py -3` |
| Error de compilación al instalar SciPy/CoolProp | Use una versión de Python con ruedas binarias (3.11–3.13 de 64 bits) |
| La ventana se ve muy pequeña o muy grande | Ajuste la escala de Windows; la interfaz es compatible con alta densidad de píxeles |
| No se abre el PDF generado | Verifique que exista un visor de PDF predeterminado |
| Antivirus bloquea el .exe | Agregue la carpeta `dist\HVAC_Calculator` a las exclusiones (falso positivo habitual de PyInstaller) |

## Desinstalación

Borre la carpeta del programa y, si lo desea, `%APPDATA%\HVAC_Industrial_Calculator`.
