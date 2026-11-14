<#
.SYNOPSIS
    Starts the BloodConnect Backend Server and opens the client in the default browser.
.DESCRIPTION
    Detects the active Python 3 runtime on the system (supporting standard python, py launcher,
    and the LibreOffice Python 3.11 engine), starts the threaded REST API server, and automatically
    opens http://localhost:5000/.
#>

param(
    [int]$Port = 5000
)

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         BloodConnect Emergency Blood Network" -ForegroundColor Red
Write-Host "                PowerShell Server Launcher" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = $null

# 1. Check verified LibreOffice Python 3.11
$loPython = "C:\Program Files\LibreOffice\program\python.exe"
if (Test-Path $loPython) {
    $pythonExe = $loPython
}

# 2. Check py launcher
if (-not $pythonExe) {
    try {
        $testPy = & py -3 -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $testPy) {
            $pythonExe = "py -3"
        }
    } catch {}
}

# 3. Check python in PATH
if (-not $pythonExe) {
    try {
        $testPy = & python -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $testPy) {
            $pythonExe = "python"
        }
    } catch {}
}

if (-not $pythonExe) {
    Write-Host "[!] Error: No working Python 3 installation was detected." -ForegroundColor Red
    Write-Host "    Please install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "[*] Selected Python Runtime: $pythonExe" -ForegroundColor Green
Write-Host "[*] Starting server on: http://localhost:$Port/" -ForegroundColor Green
Write-Host "[*] Serving static UI:   c:\Users\acer\blood connect\index.html" -ForegroundColor Gray
Write-Host "[*] REST API prefix:     http://localhost:$Port/api/" -ForegroundColor Gray
Write-Host "[*] Interactive Docs:    http://localhost:$Port/api/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to terminate the server." -ForegroundColor Yellow
Write-Host ""

# Open browser asynchronously after 1.5 seconds
Start-Job -ScriptBlock {
    param($url)
    Start-Sleep -Milliseconds 1500
    Start-Process $url
} -ArgumentList "http://localhost:$Port/" | Out-Null

# Start server process
if ($pythonExe -eq "py -3") {
    & py -3 backend\server.py $Port
} elseif ($pythonExe -eq "python") {
    & python backend\server.py $Port
} else {
    & $pythonExe backend\server.py $Port
}
