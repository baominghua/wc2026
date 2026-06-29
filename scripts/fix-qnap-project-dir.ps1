param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [int]$NasSshPort = 22,
  [string]$NasPath = "/share/CACHEDEV1_DATA/Web/wc2026"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$FixScript = Join-Path $Root "scripts/qnap-fix-project-dir.sh"

if (-not (Test-Path $FixScript)) {
  throw "Fix script not found: $FixScript"
}

Write-Host "Uploading QNAP fix script..." -ForegroundColor Cyan
& scp -P $NasSshPort $FixScript "${NasUser}@${NasHost}:/tmp/qnap-fix-project-dir.sh"
if ($LASTEXITCODE -ne 0) {
  throw "Upload failed with exit code $LASTEXITCODE"
}

Write-Host "Running QNAP fix script..." -ForegroundColor Cyan
& ssh -p $NasSshPort "${NasUser}@${NasHost}" "sh /tmp/qnap-fix-project-dir.sh '$NasPath'"
if ($LASTEXITCODE -ne 0) {
  throw "Remote fix failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Try Container Station again, or run the printed docker compose command on NAS." -ForegroundColor Green
