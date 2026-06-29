param(
  [string]$NasHost = "192.168.100.185",
  [string]$AfterHost = "192.168.100.250",
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
$LocalLog = Join-Path $env:TEMP ("wc2026-fix-qvs0-route-cutover-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$KnownHosts = Join-Path $env:TEMP "wc2026-nas-known-hosts"
$SshOptions = @("-o", "UserKnownHostsFile=$KnownHosts", "-o", "StrictHostKeyChecking=accept-new")

function Run-CurlHead([string]$Url) {
  Write-Host ""
  Write-Host "TEST $Url" -ForegroundColor Yellow
  curl.exe -I --max-time 8 $Url | Out-Host
}

try {
  Write-Host "WC2026 NAS qvs0 stale-route cutover fix" -ForegroundColor Cyan
  Write-Host "Current reachable host: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
  Write-Host "Expected restored host: $AfterHost" -ForegroundColor Cyan
  Write-Host "Action: schedule deletion of 192.168.100.0/24 dev qvs0 after SSH exits." -ForegroundColor Yellow
  Write-Host "You may be asked for the NAS password two or three times." -ForegroundColor Yellow
  Write-Host "Local log target: $LocalLog" -ForegroundColor DarkGray

  & scp @SshOptions -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
  if ($LASTEXITCODE -ne 0) {
    throw "Upload failed with exit code $LASTEXITCODE."
  }

  $remoteCommand = "nohup sh -c 'sleep 2; sh $RemoteScript $RemoteLog $ClientIp $AppPort' >/tmp/wc2026-fix-qvs0-route-start.out 2>&1 &"
  & ssh @SshOptions -p $NasSshPort "${NasUser}@${NasHost}" $remoteCommand
  if ($LASTEXITCODE -ne 0) {
    throw "Remote scheduling failed with exit code $LASTEXITCODE."
  }

  Write-Host ""
  Write-Host "Route fix scheduled. Waiting for NAS to switch return path..." -ForegroundColor Cyan
  Start-Sleep -Seconds 8

  Write-Host ""
  Write-Host "===== Windows-side tests =====" -ForegroundColor Cyan
  ping -n 2 $AfterHost | Out-Host
  Run-CurlHead "http://$AfterHost`:8088/"
  Run-CurlHead "http://$AfterHost`:$AppPort/tournament"
  Run-CurlHead "http://bmhlfc.top`:$PublicPort/tournament"

  Write-Host ""
  Write-Host "===== Try downloading NAS log =====" -ForegroundColor Cyan
  $downloaded = $false
  foreach ($hostCandidate in @($AfterHost, $NasHost)) {
    if ($downloaded) { break }
    Write-Host "Trying $hostCandidate..." -ForegroundColor DarkGray
    & scp @SshOptions -P $NasSshPort "${NasUser}@${hostCandidate}:$RemoteLog" $LocalLog
    if ($LASTEXITCODE -eq 0) {
      $downloaded = $true
      Write-Host "Downloaded log from $hostCandidate" -ForegroundColor Green
    }
  }

  if ($downloaded) {
    Write-Host ""
    Write-Host "===== NAS route-fix log =====" -ForegroundColor Cyan
    Get-Content $LocalLog
  } else {
    Write-Host "Could not download the NAS log, but the Windows-side tests above are the main proof." -ForegroundColor Yellow
  }

  Write-Host ""
  Write-Host "Done." -ForegroundColor Green
} catch {
  Write-Host ""
  Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
  throw
} finally {
  Read-Host "Press Enter to close"
}
