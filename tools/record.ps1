# SOEN 321 - record one experiment run.
# Usage:  powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant sider -Experiment E1 -Run 1
# Opens Edge (its own test profile for that assistant) with all traffic going through mitmproxy.
# Do the experiment, then CLOSE THAT EDGE WINDOW. The recording is saved when Edge closes.
param(
    [Parameter(Mandatory)] [ValidateSet("copilot","sider","merlin","perplexity","dryrun","baseline")] [string]$Assistant,
    [Parameter(Mandatory)] [ValidatePattern("^E[0-4]$")] [string]$Experiment,
    [Parameter(Mandatory)] [ValidateRange(1,9)] [int]$Run,
    [string]$Url = "http://127.0.0.1:8765/",
    [switch]$Force
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path tools\spki.txt)) { throw "Run tools\setup.ps1 first." }
$spki = (Get-Content tools\spki.txt).Trim()

$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw "Microsoft Edge not found." }

$outDir = "evidence\$Assistant"; New-Item -ItemType Directory -Force $outDir, "$outDir\screenshots" | Out-Null
$flow = "$outDir\${Experiment}_run$Run.flow"
if ((Test-Path $flow) -and -not $Force) { throw "$flow already exists. Use a different -Run number, or add -Force to overwrite." }
if (Test-Path $flow) { Remove-Item $flow }

# Stop a recorder or test-page server left running by an earlier script that was interrupted (only ours, from .venv)
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like "$root\.venv\*" -and ($_.Name -eq "mitmdump.exe" -or $_.CommandLine -like "*http.server*") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# Local server for our test pages
$server = Start-Process .venv\Scripts\python.exe -ArgumentList "-m http.server 8765 --bind 127.0.0.1 --directory test_pages" -PassThru -WindowStyle Hidden

# mitmproxy, writing every request/response to the .flow file
$env:SOEN_STOP_FILE = Join-Path $root "tools\.stop"
if (Test-Path $env:SOEN_STOP_FILE) { Remove-Item $env:SOEN_STOP_FILE }
$mitm = Start-Process .venv\Scripts\mitmdump.exe -PassThru -WindowStyle Minimized -ArgumentList @(
    "--listen-host 127.0.0.1", "--listen-port 8899", "-w `"$flow`"", "-s tools\stop_on_file.py")
Start-Sleep -Seconds 3
if ($mitm.HasExited) { Stop-Process -Id $server.Id -Force; throw "mitmdump failed to start (is port 8899 already in use?)" }

# Edge with its own profile per assistant; trusts only mitmproxy's key, only in this window
$profileDir = Join-Path $root "profiles\$Assistant"
$started = Get-Date
Write-Host "Recording to $flow"
Write-Host ">>> Do the experiment in the Edge window that opens, then CLOSE that window to finish. <<<"
$edgeProc = Start-Process $edge -PassThru -ArgumentList @(
    "--user-data-dir=`"$profileDir`"",
    "--proxy-server=http://127.0.0.1:8899",
    "--proxy-bypass-list=`"<-loopback>`"",
    "--ignore-certificate-errors-spki-list=$spki",
    "--no-first-run", "--no-default-browser-check",
    $Url)
$edgeProc.WaitForExit()

# Stop mitmproxy cleanly so the file is complete
New-Item -ItemType File $env:SOEN_STOP_FILE | Out-Null
if (-not $mitm.WaitForExit(15000)) { Stop-Process -Id $mitm.Id -Force; Write-Warning "mitmdump had to be force-stopped; the last few requests may be missing." }
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue

$edgeVersion = (Get-Item $edge).VersionInfo.ProductVersion
$note = "- $($started.ToString('yyyy-MM-dd HH:mm')) | $Experiment run $Run | Edge $edgeVersion | $([math]::Round((Get-Item $flow).Length/1KB)) KB | notes: "
Add-Content "$outDir\lab_notes.md" $note
Write-Host "`nSaved $flow ($([math]::Round((Get-Item $flow).Length/1KB)) KB). A line was added to $outDir\lab_notes.md - add your notes there."
Write-Host "Check it:  powershell -ExecutionPolicy Bypass -File tools\analyze.ps1"
