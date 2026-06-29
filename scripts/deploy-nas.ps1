param(
  [string]$NasHost = "bmhlfc.top",
  [string]$NasUser = "admin",
  [string]$NasPath = "/share/CACHEDEV1_DATA/Web/wc2026",
  [int]$AppPort = 12302,
  [int]$NasSshPort = 22,
  [string]$AdminPassword = "",
  [string]$AuthSessionSecret = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Package = Join-Path $Root "wc2026-nas-docker.tar.gz"
$RemotePackage = "$NasPath/.deploy-wc2026-nas-docker.tar.gz"

function ConvertTo-ShellSingleQuoted {
  param([string]$Value)
  return "'" + $Value.Replace("'", '''"''"''') + "'"
}

if ($AdminPassword -and -not $AuthSessionSecret) {
  $AuthSessionSecret = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
}

$AdminPasswordLiteral = ConvertTo-ShellSingleQuoted $AdminPassword
$AuthSessionSecretLiteral = ConvertTo-ShellSingleQuoted $AuthSessionSecret

Write-Host "Packaging project..." -ForegroundColor Cyan
Push-Location $Root
try {
  Write-Host "Checking SSH access to $NasHost`:$NasSshPort..." -ForegroundColor Cyan
  $sshReachable = Test-NetConnection -ComputerName $NasHost -Port $NasSshPort -InformationLevel Quiet
  if (-not $sshReachable) {
    throw "Cannot connect to $NasHost`:$NasSshPort. Enable QNAP SSH, check firewall/router forwarding, or use the NAS LAN IP."
  }

  if (Test-Path $Package) {
    Remove-Item -LiteralPath $Package -Force
  }

  tar `
    --exclude="./frontend/node_modules" `
    --exclude="./frontend/dist" `
    --exclude="./frontend/*.log" `
    --exclude="./frontend/*.tar.gz" `
    --exclude="./.venvs" `
    --exclude="./.pytest_cache" `
    --exclude="./**/__pycache__" `
    --exclude="./artifacts" `
    --exclude="./wc2026-codex-video" `
    --exclude="./backend/venv" `
    --exclude="./backend/__pycache__" `
    --exclude="./backend/*/__pycache__" `
    --exclude="./backend/**/__pycache__" `
    --exclude="./backend/*.log" `
    --exclude="./backend/**/*.log" `
    --exclude="./backend/wc2026.db" `
    --exclude="./backend/data/matches.live.json" `
    --exclude="./backend/data/prediction_snapshots.json" `
    --exclude="./output" `
    --exclude="./.workbuddy" `
    --exclude="./wc2026-nas-docker.zip" `
    --exclude="./wc2026-nas-docker.tar.gz" `
    --exclude="./*.zip" `
    --exclude="./*.log" `
    --exclude="./*.tar.gz" `
    -czf $Package .
  if ($LASTEXITCODE -ne 0) {
    throw "Packaging failed with exit code $LASTEXITCODE."
  }

  Write-Host "Preparing remote project storage at $NasPath..." -ForegroundColor Cyan
  & ssh -p $NasSshPort "${NasUser}@${NasHost}" "mkdir -p '$NasPath' && rm -f '$RemotePackage'"
  if ($LASTEXITCODE -ne 0) {
    throw "Remote project storage preparation failed with exit code $LASTEXITCODE."
  }

  Write-Host "Uploading to $NasUser@${NasHost}:$RemotePackage..." -ForegroundColor Cyan
  & scp -P $NasSshPort $Package "${NasUser}@${NasHost}:$RemotePackage"
  if ($LASTEXITCODE -ne 0) {
    throw "Upload failed with exit code $LASTEXITCODE."
  }

  $RemoteCommand = @"
export PATH="/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/docker/bin:/share/CACHEDEV1_DATA/.qpkg/container-station/sbin:/opt/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:`$PATH" &&
command -v docker >/dev/null 2>&1 || { echo "docker not found in non-interactive SSH PATH: `$PATH"; exit 127; } &&
mkdir -p '$NasPath' &&
tar -xzf '$RemotePackage' -C '$NasPath' &&
cd '$NasPath' &&
if [ ! -f .env ]; then cp .env.nas.example .env; fi &&
sed -i 's/^APP_PORT=.*/APP_PORT=$AppPort/' .env &&
grep -q '^AUTH_ENABLED=' .env || printf '\nAUTH_ENABLED=true\n' >> .env &&
grep -q '^ADMIN_PASSWORD=' .env || printf 'ADMIN_PASSWORD=\n' >> .env &&
grep -q '^AUTH_SESSION_SECRET=' .env || printf 'AUTH_SESSION_SECRET=\n' >> .env &&
grep -q '^AUTH_SESSION_MAX_AGE_SECONDS=' .env || printf 'AUTH_SESSION_MAX_AGE_SECONDS=604800\n' >> .env &&
grep -q '^AUTH_COOKIE_SECURE=' .env || printf 'AUTH_COOKIE_SECURE=false\n' >> .env &&
if [ -n $AdminPasswordLiteral ]; then grep -v '^ADMIN_PASSWORD=' .env > .env.tmp && printf 'ADMIN_PASSWORD=%s\n' $AdminPasswordLiteral >> .env.tmp && mv .env.tmp .env; fi &&
if [ -n $AuthSessionSecretLiteral ]; then grep -v '^AUTH_SESSION_SECRET=' .env > .env.tmp && printf 'AUTH_SESSION_SECRET=%s\n' $AuthSessionSecretLiteral >> .env.tmp && mv .env.tmp .env; fi &&
grep -q '^ESPN_SCOREBOARD_ENABLED=' .env || printf '\nESPN_SCOREBOARD_ENABLED=true\n' >> .env &&
grep -v '^ESPN_SCOREBOARD_START_DATE=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_START_DATE=20260611\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_MAX_DAYS=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_MAX_DAYS=60\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_DAYS_BACK=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_DAYS_BACK=14\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_DAYS_FORWARD=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_DAYS_FORWARD=2\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_TIMEOUT_SECONDS=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_TIMEOUT_SECONDS=8\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_MAX_WORKERS=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_MAX_WORKERS=6\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^LOCAL_MATCH_FEED_ENABLED=' .env > .env.tmp && printf 'LOCAL_MATCH_FEED_ENABLED=true\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^API_FOOTBALL_ENABLED=' .env > .env.tmp && printf 'API_FOOTBALL_ENABLED=true\n' >> .env.tmp && mv .env.tmp .env &&
grep -q '^API_FOOTBALL_KEY=' .env || printf 'API_FOOTBALL_KEY=\n' >> .env &&
grep -q '^API_FOOTBALL_LEAGUE_ID=' .env || printf 'API_FOOTBALL_LEAGUE_ID=1\n' >> .env &&
grep -q '^API_FOOTBALL_SEASON=' .env || printf 'API_FOOTBALL_SEASON=2026\n' >> .env &&
grep -q '^API_FOOTBALL_DETAIL_DAYS_BACK=' .env || printf 'API_FOOTBALL_DETAIL_DAYS_BACK=7\n' >> .env &&
grep -q '^API_FOOTBALL_DETAIL_DAYS_FORWARD=' .env || printf 'API_FOOTBALL_DETAIL_DAYS_FORWARD=1\n' >> .env &&
grep -q '^SPORTMONKS_ENABLED=' .env || printf 'SPORTMONKS_ENABLED=true\n' >> .env &&
grep -q '^SPORTMONKS_TOKEN=' .env || printf 'SPORTMONKS_TOKEN=\n' >> .env &&
grep -q '^SPORTMONKS_TIMEOUT_SECONDS=' .env || printf 'SPORTMONKS_TIMEOUT_SECONDS=12\n' >> .env &&
grep -q '^SPORTMONKS_TEAM_IDS_JSON=' .env || printf 'SPORTMONKS_TEAM_IDS_JSON=\n' >> .env &&
docker compose --env-file .env up -d --build &&
rm -f '$RemotePackage'
"@ -replace "`r?`n", " "

  Write-Host "Starting Docker Compose on NAS..." -ForegroundColor Cyan
  & ssh -p $NasSshPort "${NasUser}@${NasHost}" $RemoteCommand
  if ($LASTEXITCODE -ne 0) {
    throw "Remote Docker Compose failed with exit code $LASTEXITCODE."
  }

  Write-Host "Done. NAS app port is $AppPort. Public route is usually http://$NasHost`:12026/ when the router forwards 12026 to $AppPort." -ForegroundColor Green
}
finally {
  Pop-Location
}
