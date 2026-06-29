param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$NasPath = "/share/CACHEDEV1_DATA/Web/wc2026"
)

$ErrorActionPreference = "Stop"

$LocalScript = Join-Path $PSScriptRoot "diagnose-nas-network.sh"
$RemoteScript = "/tmp/wc2026-diagnose-network.sh"
$RemoteLog = "/tmp/wc2026-network-diag.log"
$LocalLog = Join-Path $env:TEMP ("wc2026-network-diag-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "WC2026 NAS network diagnostics" -ForegroundColor Cyan
Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
Write-Host "You may be asked for the NAS password three times: upload, execute, download." -ForegroundColor Yellow
Write-Host "Local log will be: $LocalLog" -ForegroundColor DarkGray

& scp -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
if ($LASTEXITCODE -ne 0) {
  throw "Upload failed with exit code $LASTEXITCODE."
}

& ssh -tt -p $NasSshPort "${NasUser}@${NasHost}" "sh '$RemoteScript' '$RemoteLog' '$NasPath'"
if ($LASTEXITCODE -ne 0) {
  throw "Remote diagnostics failed with exit code $LASTEXITCODE."
}

& scp -P $NasSshPort "${NasUser}@${NasHost}:$RemoteLog" $LocalLog
if ($LASTEXITCODE -ne 0) {
  throw "Download failed with exit code $LASTEXITCODE."
}

Write-Host "Diagnostics saved to $LocalLog" -ForegroundColor Green
Get-Content $LocalLog
Read-Host "Press Enter to close"
