param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$ClientIp = "192.168.100.26",
  [int]$AppPort = 12302,
  [int]$PublicPort = 12026
)

$ErrorActionPreference = "Stop"

$LocalScript = Join-Path $PSScriptRoot "fix-nas-qvs0-route.sh"
$RemoteScript = "/tmp/wc2026-fix-qvs0-route.sh"
$RemoteLog = "/tmp/wc2026-fix-qvs0-route.log"
$LocalLog = Join-Path $env:TEMP ("wc2026-fix-qvs0-route-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "WC2026 NAS qvs0 stale-route fix" -ForegroundColor Cyan
Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
Write-Host "Action: delete 192.168.100.0/24 dev qvs0, then flush route cache" -ForegroundColor Yellow
Write-Host "You may be asked for the NAS password three times: upload, run, download." -ForegroundColor Yellow
Write-Host "Local log will be: $LocalLog" -ForegroundColor DarkGray

& scp -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
if ($LASTEXITCODE -ne 0) {
  throw "Upload failed with exit code $LASTEXITCODE."
}

& ssh -p $NasSshPort "${NasUser}@${NasHost}" "sh '$RemoteScript' '$RemoteLog' '$ClientIp' '$AppPort'"
if ($LASTEXITCODE -ne 0) {
  throw "Remote route fix failed with exit code $LASTEXITCODE."
}

& scp -P $NasSshPort "${NasUser}@${NasHost}:$RemoteLog" $LocalLog
if ($LASTEXITCODE -ne 0) {
  throw "Download failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "===== NAS route-fix log =====" -ForegroundColor Cyan
Get-Content $LocalLog

Write-Host ""
Write-Host "===== Windows-side tests =====" -ForegroundColor Cyan
$urls = @(
  "http://192.168.100.250:$AppPort/",
  "http://192.168.100.250:$AppPort/tournament",
  "http://$NasHost`:$PublicPort/tournament"
)

foreach ($url in $urls) {
  Write-Host ""
  Write-Host "TEST $url" -ForegroundColor Yellow
  curl.exe -I --max-time 8 $url | Out-Host
}

Write-Host ""
Write-Host "Done. If the tests show HTTP 200, the old qvs0 route was the cause." -ForegroundColor Green
Read-Host "Press Enter to close"
