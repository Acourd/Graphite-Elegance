# Isoform launcher - runs the shared engine with this theme's config.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $ScriptDir "..\Tools\icon_engine.py"
$Config = Join-Path $ScriptDir "theme.json"

Write-Host "Aplicando Graphite Elegance..." -ForegroundColor Cyan
if (-not (Test-Path $Engine)) {
    Write-Error "No se encontró el motor en $Engine"
    exit 1
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $Engine --config $Config
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python $Engine --config $Config
} else {
    Write-Error "Python 3 no está instalado."
}

Write-Host "`nSi los iconos no se actualizan, presiona F5 en el escritorio." -ForegroundColor Green
Start-Sleep -Seconds 3
