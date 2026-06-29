param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$ClientIp = "192.168.100.26",
  [int]$AppPort = 12302,
  [int]$PublicPort = 12026
)

$ErrorActionPreference = "Stop"

$LocalScript = Join-Path $PSScriptRoot "capture-nas-wc2026-port.sh"
$RemoteScript = "/tmp/wc2026-port-capture.sh"
$RemoteLog = "/tmp/wc2026-port-capture.log"
$LocalLog = Join-Path $env:TEMP ("wc2026-port-capture-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "WC2026 NAS packet capture" -ForegroundColor Cyan
Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
Write-Host "Client: $ClientIp, ports: $AppPort and $PublicPort" -ForegroundColor Yellow
Write-Host "You may be asked for the NAS password three times: upload, start capture, download." -ForegroundColor Yellow
Write-Host "Local log will be: $LocalLog" -ForegroundColor DarkGray

& scp -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
if ($LASTEXITCODE -ne 0) {
  throw "Upload failed with exit code $LASTEXITCODE."
}

Write-Host "Starting remote capture for 15 seconds..." -ForegroundColor Cyan
& ssh -p $NasSshPort "${NasUser}@${NasHost}" "nohup sh '$RemoteScript' '$RemoteLog' '$ClientIp' '$AppPort' '$PublicPort' >/tmp/wc2026-port-capture-run.out 2>&1 &"
if ($LASTEXITCODE -ne 0) {
  throw "Remote capture start failed with exit code $LASTEXITCODE."
}

Start-Sleep -Seconds 2

Write-Host "Triggering local connection attempts..." -ForegroundColor Cyan
curl.exe -I --max-time 4 "http://192.168.100.250:$AppPort/" | Out-Host
curl.exe -I --max-time 4 "http://192.168.100.185:$AppPort/" | Out-Host
curl.exe -I --max-time 4 "http://$NasHost`:$PublicPort/" | Out-Host

Start-Sleep -Seconds 16

& scp -P $NasSshPort "${NasUser}@${NasHost}:$RemoteLog" $LocalLog
if ($LASTEXITCODE -ne 0) {
  throw "Download failed with exit code $LASTEXITCODE."
}

Write-Host "Capture saved to $LocalLog" -ForegroundColor Green
Get-Content $LocalLog
Read-Host "Press Enter to close"
