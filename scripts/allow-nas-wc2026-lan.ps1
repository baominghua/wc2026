param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$LanCidr = "192.168.100.0/24",
  [int]$AppPort = 12302
)

$ErrorActionPreference = "Stop"

$LocalScript = Join-Path $PSScriptRoot "allow-nas-wc2026-lan.sh"
$RemoteScript = "/tmp/wc2026-allow-lan.sh"
$RemoteLog = "/tmp/wc2026-allow-lan.log"
$LocalLog = Join-Path $env:TEMP ("wc2026-allow-lan-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "WC2026 NAS LAN allow rule" -ForegroundColor Cyan
Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
Write-Host "Allow: $LanCidr -> tcp/$AppPort in QUFIREWALL" -ForegroundColor Yellow
Write-Host "This is a narrow iptables rule. It may be reset by QuFirewall/reboot unless added in the QNAP UI." -ForegroundColor Yellow
Write-Host "You may be asked for the NAS password three times: upload, execute, download." -ForegroundColor Yellow
Write-Host "Local log will be: $LocalLog" -ForegroundColor DarkGray

& scp -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
if ($LASTEXITCODE -ne 0) {
  throw "Upload failed with exit code $LASTEXITCODE."
}

& ssh -tt -p $NasSshPort "${NasUser}@${NasHost}" "sh '$RemoteScript' '$RemoteLog' '$LanCidr' '$AppPort'"
if ($LASTEXITCODE -ne 0) {
  throw "Remote allow failed with exit code $LASTEXITCODE."
}

& scp -P $NasSshPort "${NasUser}@${NasHost}:$RemoteLog" $LocalLog
if ($LASTEXITCODE -ne 0) {
  throw "Download failed with exit code $LASTEXITCODE."
}

Write-Host "Allow rule applied. Log saved to $LocalLog" -ForegroundColor Green
Get-Content $LocalLog
Read-Host "Press Enter to close"
