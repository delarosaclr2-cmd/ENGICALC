param([string]$Python = 'python', [string]$Destino = '')
$ErrorActionPreference = 'Stop'
$repoPortable = Split-Path -Parent $PSScriptRoot
$pythonPortable = (Get-Command $Python -ErrorAction Stop).Source
if (-not $Destino) {
    $Destino = Join-Path $repoPortable ('dist\portable_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
}
$runPortable = [IO.Path]::GetFullPath($Destino)
if (Test-Path -LiteralPath $runPortable) { throw "El destino ya existe: $runPortable. Use una carpeta nueva." }
& $pythonPortable -c "import sys,struct,PyInstaller; assert sys.platform=='win32' and struct.calcsize('P')==8, 'Se requiere Windows y Python x64'"
if ($LASTEXITCODE -ne 0) { throw 'No se cumple el entorno de compilacion.' }
New-Item -ItemType Directory -Path $runPortable | Out-Null
$distPortable = Join-Path $runPortable 'compilados'
$workPortable = Join-Path $runPortable 'trabajo'
$pathAnteriorPortable = $env:PATH
try {
    # Evita recoger DLL de herramientas ajenas (por ejemplo ICU de Poppler).
    # Qt en Windows usa la ICU del sistema, no una biblioteca encontrada en PATH.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$(Split-Path -Parent $pythonPortable)"
    foreach ($specPortable in @('empaquetado\engicalc.spec', 'HVAC_INDUSTRIAL_CALCULATOR\hvac_calculator.spec')) {
        & $pythonPortable -m PyInstaller --noconfirm --distpath $distPortable --workpath $workPortable (Join-Path $repoPortable $specPortable)
        if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion de $specPortable. Revise la salida; se conservaron los archivos." }
    }
} finally {
    $env:PATH = $pathAnteriorPortable
}
$appPortable = Join-Path $distPortable 'ENGICALC'
$hvacOrigenPortable = [IO.Path]::GetFullPath((Join-Path $distPortable 'HVAC_Calculator'))
$hvacDestinoPortable = [IO.Path]::GetFullPath((Join-Path $appPortable 'HVAC_INDUSTRIAL_CALCULATOR'))
$limitePortable = [IO.Path]::GetFullPath($distPortable).TrimEnd('\') + '\'
foreach ($rutaPortable in @($hvacOrigenPortable, $hvacDestinoPortable)) {
    if (-not $rutaPortable.StartsWith($limitePortable, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta fuera de la carpeta de compilacion: $rutaPortable"
    }
}
if (Test-Path -LiteralPath $hvacDestinoPortable) { throw 'La carpeta de HVAC de destino ya existe.' }
Move-Item -LiteralPath $hvacOrigenPortable -Destination $hvacDestinoPortable
Set-Content -LiteralPath (Join-Path $appPortable 'portable.flag') -Value 'ENGICALC portable' -Encoding utf8
& $pythonPortable (Join-Path $repoPortable 'empaquetado\verificar_portable.py') $appPortable (Join-Path $runPortable 'verificacion')
if ($LASTEXITCODE -ne 0) { throw 'La distribucion no supero la verificacion; no se genero un ZIP de entrega.' }
& $pythonPortable (Join-Path $repoPortable 'empaquetado\finalizar_portable.py') $appPortable $runPortable
if ($LASTEXITCODE -ne 0) { throw 'No se pudo finalizar el ZIP portable.' }
