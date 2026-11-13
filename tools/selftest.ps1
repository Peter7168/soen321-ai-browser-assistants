# SOEN 321 - automatic end-to-end check (no clicking needed). Writes tools\selftest\result.txt
# Usage: powershell -ExecutionPolicy Bypass -File tools\selftest.ps1 [-Visible]
param([switch]$Visible)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$T = "tools\selftest"; New-Item -ItemType Directory -Force "$T\evidence\selftest" | Out-Null
$log = "$T\result.txt"
"selftest started $(Get-Date -Format s)" | Out-File $log -Encoding utf8
function L($m) { $m | Out-File $log -Append -Encoding utf8 }
try {
    $spki = (Get-Content tools\spki.txt).Trim(); L "spki=$spki"
    $edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe","$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    L "edge=$edge $((Get-Item $edge).VersionInfo.ProductVersion)"
    $flow = "$T\evidence\selftest\E0_run1.flow"; if (Test-Path $flow) { Remove-Item $flow }
    $server = Start-Process .venv\Scripts\python.exe -ArgumentList "-m http.server 18765 --bind 127.0.0.1 --directory test_pages" -PassThru -WindowStyle Hidden -RedirectStandardError "$T\server.log"
    $env:SOEN_STOP_FILE = Join-Path $root "$T\.stop"; if (Test-Path $env:SOEN_STOP_FILE) { Remove-Item $env:SOEN_STOP_FILE }
    $mitm = Start-Process .venv\Scripts\mitmdump.exe -PassThru -WindowStyle Hidden -RedirectStandardOutput "$T\mitm.log" -RedirectStandardError "$T\mitm.err" -ArgumentList @(
        "--listen-host 127.0.0.1", "--listen-port 18899", "-w `"$flow`"", "-s tools\stop_on_file.py")
    Start-Sleep 3; L "mitm running=$(-not $mitm.HasExited) server running=$(-not $server.HasExited)"
    $prof = Join-Path $root "profiles\selftest"
    $eargs = @("--user-data-dir=`"$prof`"", "--proxy-server=http://127.0.0.1:18899", "--proxy-bypass-list=`"<-loopback>`"",
              "--ignore-certificate-errors-spki-list=$spki", "--no-first-run", "--no-default-browser-check",
              "http://127.0.0.1:18765/dryrun.html?auto=1")
    if (-not $Visible) { $eargs = @("--headless=new") + $eargs }
    $e = Start-Process $edge -PassThru -ArgumentList $eargs
    Start-Sleep 15
    Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object { $_.CommandLine -like "*profiles\selftest*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType File $env:SOEN_STOP_FILE | Out-Null
    $clean = $mitm.WaitForExit(15000); if (-not $clean) { Stop-Process -Id $mitm.Id -Force }
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    L "mitm stopped cleanly=$clean ; flow bytes=$((Get-Item $flow -ErrorAction SilentlyContinue).Length)"
    L "---- server log (page reports) ----"; Get-Content "$T\server.log" -ErrorAction SilentlyContinue | Select-String "report|fake-assistant" | ForEach-Object { L $_.Line }
    L "---- mitm log (example.com / errors) ----"; Get-Content "$T\mitm.log","$T\mitm.err" -ErrorAction SilentlyContinue | Select-String -Pattern "wikipedia|error|Error|fail|refused" | Select-Object -First 40 | ForEach-Object { L $_.Line }
    L "---- analysis ----"
    & .venv\Scripts\python.exe analysis\analyze_flows.py "$T\evidence" test_pages\markers.csv "$T\out" 2>&1 | ForEach-Object { L "$_" }
} catch { L "EXCEPTION: $_" }
L "selftest finished $(Get-Date -Format s)"
