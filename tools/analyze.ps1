# SOEN 321 - analyze every recording in evidence\ against test_pages\markers.csv
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& .venv\Scripts\python.exe analysis\analyze_flows.py evidence test_pages\markers.csv analysis\output
