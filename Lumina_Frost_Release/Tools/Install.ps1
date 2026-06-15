# Lumina Frost — Setup
# Installs the required Python dependency (pypiwin32) and applies icons to your Desktop.
#
# Recommended: double-click Install.bat instead of this file directly.
# (Running .ps1 files may be blocked by Windows execution policy by default.)

Write-Host ""
Write-Host "Lumina Frost — Setup" -ForegroundColor Cyan
Write-Host "--------------------"
Write-Host ""

try {
    # ── 1. Locate Python 3 ────────────────────────────────────────────────────
    $python = $null
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python 3") {
                $python = $cmd
                break
            }
        } catch { }
    }

    if (-not $python) {
        Write-Host "[ERROR] Python 3 was not found on this machine." -ForegroundColor Red
        Write-Host ""
        Write-Host "  Download it from: https://www.python.org/downloads/"
        Write-Host "  During installation, check 'Add Python to PATH'."
        Write-Host ""
        return
    }

    $verString = (& $python --version 2>&1).ToString().Trim()
    Write-Host "[OK] Found $verString" -ForegroundColor Green

    # ── 2. Install pypiwin32 ──────────────────────────────────────────────────
    Write-Host ""
    Write-Host "Installing pypiwin32..." -ForegroundColor Yellow
    & $python -m pip install pypiwin32 --quiet

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] pip install failed." -ForegroundColor Red
        Write-Host "        Try right-clicking Install.bat and choosing 'Run as Administrator'."
        Write-Host ""
        return
    }

    Write-Host "[OK] pypiwin32 installed." -ForegroundColor Green

    # ── 3. Run the icon applicator ────────────────────────────────────────────
    Write-Host ""
    Write-Host "Applying icons to Desktop..." -ForegroundColor Cyan
    Write-Host ""

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    & $python "$scriptDir\apply_desktop_icons.py"

} catch {
    Write-Host ""
    Write-Host "[ERROR] $_" -ForegroundColor Red
} finally {
    Write-Host ""
    Read-Host "Press Enter to close"
}
