# Isoform launcher - runs the shared engine with this theme's config.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $ScriptDir "..\Tools\icon_engine.py"
$Config = Join-Path $ScriptDir "theme.json"

if (-not (Test-Path $Engine)) {
    Write-Error "No se encontro el motor en $Engine"
    exit 1
}

$exeName = $null
$exeArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $exeName = 'py'; $exeArgs = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $exeName = 'python'
}

if (-not $exeName) {
    Write-Error "Python 3 no esta instalado o no esta en PATH."
    exit 1
}

Write-Host "Aplicando Graphite Elegance..." -ForegroundColor Cyan
& $exeName @exeArgs $Engine --config $Config
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Error "El motor termino con codigo $code."
    exit $code
}
Write-Host "`nSi los iconos no se actualizan, presiona F5 en el escritorio." -ForegroundColor Green
Start-Sleep -Seconds 3
exit 0