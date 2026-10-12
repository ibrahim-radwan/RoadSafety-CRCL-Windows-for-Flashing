param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PcapPath,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$OutputDir
)

$ErrorActionPreference = 'Stop'

function Fail($Message) {
    throw "ERROR: $Message"
}

if (-not (Test-Path -LiteralPath $PcapPath)) {
    Fail "Capture file not found: $PcapPath"
}

$sourceItem = Get-Item -LiteralPath $PcapPath
if ($sourceItem.PSIsContainer) {
    Fail "The capture path must be a file, not a directory: $PcapPath"
}

$tsPath = 'C:\Program Files\Wireshark\tshark.exe'
if (-not (Test-Path -LiteralPath $tsPath)) {
    $alt = Get-ChildItem -Path 'C:\' -Filter 'tshark.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $alt) {
        Fail "TShark was not found. Install Wireshark or ensure tshark.exe is available on PATH."
    }
    $tsPath = $alt.FullName
}

$resolvedOut = [System.IO.Path]::GetFullPath($OutputDir)
if (-not (Test-Path -LiteralPath $resolvedOut)) {
    New-Item -ItemType Directory -Path $resolvedOut -Force | Out-Null
}

$analysisDir = Join-Path $resolvedOut 'radar_capture_analysis'
New-Item -ItemType Directory -Path $analysisDir -Force | Out-Null

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir 'analyze_capture.py'
if (-not (Test-Path -LiteralPath $pythonScript)) {
    Fail "Required helper script not found: $pythonScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) {
        Fail "Python is required to aggregate the extracted packet CSV and summarize traffic."
    }
    $python = $py
}

& $python.Source $pythonScript `"$PcapPath`" `"$resolvedOut`"
if ($LASTEXITCODE -ne 0) {
    Fail "The analysis helper exited with code $LASTEXITCODE."
}

$allFiles = Get-ChildItem -Path $analysisDir -File | Sort-Object Name
Write-Host "Generated files:"
foreach ($f in $allFiles) {
    Write-Host " - $($f.Name)"
}

Write-Host "Finished: $analysisDir"
