param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$NasPath = "/share/CACHEDEV1_DATA/Web/wc2026"
)

$ErrorActionPreference = "Stop"

$ScriptRoot = $PSScriptRoot
$LocalScript = Join-Path $ScriptRoot "repair-nas-port.sh"
$RemoteScript = "/tmp/wc2026-repair-nas-port.sh"
$TranscriptPath = Join-Path $env:TEMP ("wc2026-repair-nas-port-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Start-Transcript -Path $TranscriptPath | Out-Null
try {
  Write-Host "WC2026 NAS port repair" -ForegroundColor Cyan
  Write-Host "Target: $NasUser@$NasHost`:$NasSshPort" -ForegroundColor Cyan
  Write-Host "You may be asked for the NAS password twice: upload, then execute." -ForegroundColor Yellow
  Write-Host "Transcript: $TranscriptPath" -ForegroundColor DarkGray

  Write-Host "Uploading repair script..." -ForegroundColor Cyan
  & scp -P $NasSshPort $LocalScript "${NasUser}@${NasHost}:$RemoteScript"
  if ($LASTEXITCODE -ne 0) {
    throw "Upload failed with exit code $LASTEXITCODE."
  }

  Write-Host "Running repair script on NAS..." -ForegroundColor Cyan
  & ssh -tt -p $NasSshPort "${NasUser}@${NasHost}" "sh '$RemoteScript' '$NasPath'"
  if ($LASTEXITCODE -ne 0) {
    throw "Remote repair failed with exit code $LASTEXITCODE."
  }

  Write-Host "Repair command completed." -ForegroundColor Green
}
finally {
  Stop-Transcript | Out-Null
  Write-Host "Transcript saved to $TranscriptPath" -ForegroundColor Cyan
  Read-Host "Press Enter to close"
}
