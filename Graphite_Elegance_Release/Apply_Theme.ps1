# Wrapper de PowerShell para aplicar el tema de iconos Graphite Elegance e invisibilizar nombres
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApplicatorScript = Join-Path $ScriptDir "Tools\apply_desktop_icons.py"

Write-Host "Iniciando aplicador estético de Graphite Elegance..." -ForegroundColor Cyan
Write-Host "Los nombres de tus accesos directos se ocultarán para lograr un diseño limpio." -ForegroundColor DarkGray

if (Test-Path $ApplicatorScript) {
    py -3 $ApplicatorScript
} else {
    Write-Error "No se encontró el script de aplicación en $ApplicatorScript"
}

Write-Host "`nProceso finalizado. Si los iconos no se actualizan, presiona F5 en el escritorio." -ForegroundColor Green
Start-Sleep -Seconds 3
