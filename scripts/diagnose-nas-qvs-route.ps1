param(
  [string]$NasHost = "192.168.100.185",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$ClientIp = "192.168.100.26"
)

$ErrorActionPreference = "Stop"

$KnownHosts = Join-Path $env:TEMP "wc2026-nas-known-hosts"
$SshOptions = @("-o", "UserKnownHostsFile=$KnownHosts", "-o", "StrictHostKeyChecking=accept-new")
$LocalLog = Join-Path $env:TEMP ("wc2026-diagnose-qvs-route-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

$remoteCommand = @"
echo STEP date
date
echo STEP host
hostname
id
echo STEP routes
ip route show
echo STEP route_to_client
ip route get $ClientIp || true
echo STEP qvs0_addr
ip -4 addr show qvs0 || true
echo STEP qvs2_addr
ip -4 addr show qvs2 || true
echo STEP fix_files
ls -l /tmp/wc2026-fix-qvs0-route* 2>/dev/null || true
echo STEP start_out
cat /tmp/wc2026-fix-qvs0-route-start.out 2>/dev/null || true
echo STEP route_log_tail
tail -120 /tmp/wc2026-fix-qvs0-route.log 2>/dev/null || true
"@

try {
  Write-Host "WC2026 NAS qvs route diagnosis" -ForegroundColor Cyan
  Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
  Write-Host "This only reads state; it does not change routes." -ForegroundColor Yellow
  Write-Host "Local log will be: $LocalLog" -ForegroundColor DarkGray

  & ssh @SshOptions -p $NasSshPort "${NasUser}@${NasHost}" $remoteCommand 2>&1 | Tee-Object -FilePath $LocalLog
  if ($LASTEXITCODE -ne 0) {
    throw "Remote diagnosis failed with exit code $LASTEXITCODE."
  }

  Write-Host ""
  Write-Host "Diagnosis saved to $LocalLog" -ForegroundColor Green
} catch {
  Write-Host ""
  Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
  throw
} finally {
  Read-Host "Press Enter to close"
}
