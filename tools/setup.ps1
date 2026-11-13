# SOEN 321 - one-time setup (run once per laptop)
# Usage:  powershell -ExecutionPolicy Bypass -File tools\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# 1. Find Python
$py = $null
foreach ($c in @("py -3", "python", "python3")) {
    try { $v = Invoke-Expression "$c --version" 2>$null; if ($v -match "Python 3") { $py = $c; break } } catch {}
}
if (-not $py) { throw "Python 3 not found. Install it from python.org (tick 'Add to PATH') and re-run." }
Write-Host "Using $py ($v)"

# 2. Private virtual environment with mitmproxy (does not touch your other Python installs)
if (-not (Test-Path ".venv\Scripts\python.exe")) { Invoke-Expression "$py -m venv .venv" }
& .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .venv\Scripts\python.exe -m pip install mitmproxy --quiet
& .venv\Scripts\mitmdump.exe --version | Select-Object -First 1

# 3. Generate mitmproxy's certificate (created on first start)
$ca = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.pem"
if (-not (Test-Path $ca)) {
    $p = Start-Process .venv\Scripts\mitmdump.exe -ArgumentList "--listen-port 8899" -PassThru -WindowStyle Hidden
    for ($i = 0; $i -lt 20 -and -not (Test-Path $ca); $i++) { Start-Sleep -Milliseconds 500 }
    Stop-Process -Id $p.Id -Force
}
if (-not (Test-Path $ca)) { throw "mitmproxy certificate was not created at $ca" }

# 4. Fingerprint of that certificate's key. Edge is told to trust ONLY this key, and only in our
#    test profiles, so nothing is installed in the Windows certificate store.
& .venv\Scripts\python.exe tools\spki_hash.py $ca | Out-File -Encoding ascii tools\spki.txt
Write-Host "Certificate fingerprint saved to tools\spki.txt: $(Get-Content tools\spki.txt)"
Write-Host "`nSetup done. Next: tools\record.ps1 -Assistant dryrun -Experiment E0 -Run 1"
