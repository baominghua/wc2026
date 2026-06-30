param(
  [string]$UnraidHost = "192.168.100.251",
  [string]$UnraidUser = "root",
  [string]$UnraidPath = "/mnt/user/appdata/wc2026",
  [int]$AppPort = 2026,
  [int]$SshPort = 22,
  [string]$AdminPassword = "",
  [string]$AuthSessionSecret = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Package = Join-Path $Root "wc2026-unraid-docker.tar.gz"

function ConvertTo-ShellSingleQuoted {
  param([string]$Value)
  return "'" + $Value.Replace("'", '''"''"''') + "'"
}

if ($AdminPassword -and -not $AuthSessionSecret) {
  $AuthSessionSecret = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
}

$AdminPasswordLiteral = ConvertTo-ShellSingleQuoted $AdminPassword
$AuthSessionSecretLiteral = ConvertTo-ShellSingleQuoted $AuthSessionSecret

Write-Host "Packaging WC2026 for Unraid..." -ForegroundColor Cyan
Push-Location $Root
try {
  $sshReachable = Test-NetConnection -ComputerName $UnraidHost -Port $SshPort -InformationLevel Quiet
  if (-not $sshReachable) {
    throw "Cannot connect to $UnraidHost`:$SshPort. Check Unraid SSH service and LAN connectivity."
  }

  if (Test-Path $Package) {
    Remove-Item -LiteralPath $Package -Force
  }

  tar `
    --exclude="./frontend/node_modules" `
    --exclude="./frontend/*.log" `
    --exclude="./frontend/*.tar.gz" `
    --exclude="./**/__pycache__" `
    --exclude="./backend/venv" `
    --exclude="./backend/__pycache__" `
    --exclude="./backend/*/__pycache__" `
    --exclude="./backend/**/__pycache__" `
    --exclude="./backend/*.log" `
    --exclude="./backend/**/*.log" `
    --exclude="./backend/wc2026.db" `
    --exclude="./backend/data/*.db" `
    --exclude="./.workbuddy" `
    --exclude="./wc2026-*.tar.gz" `
    -czf $Package .
  if ($LASTEXITCODE -ne 0) {
    throw "Packaging failed with exit code $LASTEXITCODE."
  }

  Write-Host "Uploading package to $UnraidUser@$UnraidHost..." -ForegroundColor Cyan
  & scp -P $SshPort $Package "${UnraidUser}@${UnraidHost}:/tmp/wc2026-unraid-docker.tar.gz"
  if ($LASTEXITCODE -ne 0) {
    throw "Upload failed with exit code $LASTEXITCODE."
  }

  $RemoteCommand = @"
mkdir -p '$UnraidPath' &&
tar -xzf /tmp/wc2026-unraid-docker.tar.gz -C '$UnraidPath' &&
cd '$UnraidPath' &&
if [ ! -f .env ]; then cp .env.unraid.example .env; fi &&
sed -i 's/^APP_PORT=.*/APP_PORT=$AppPort/' .env &&
grep -q '^AUTH_ENABLED=' .env || printf '\nAUTH_ENABLED=true\n' >> .env &&
grep -q '^ADMIN_PASSWORD=' .env || printf 'ADMIN_PASSWORD=\n' >> .env &&
grep -q '^AUTH_SESSION_SECRET=' .env || printf 'AUTH_SESSION_SECRET=\n' >> .env &&
grep -q '^AUTH_SESSION_MAX_AGE_SECONDS=' .env || printf 'AUTH_SESSION_MAX_AGE_SECONDS=604800\n' >> .env &&
grep -q '^AUTH_COOKIE_SECURE=' .env || printf 'AUTH_COOKIE_SECURE=false\n' >> .env &&
if [ -n $AdminPasswordLiteral ]; then grep -v '^ADMIN_PASSWORD=' .env > .env.tmp && printf 'ADMIN_PASSWORD=%s\n' $AdminPasswordLiteral >> .env.tmp && mv .env.tmp .env; fi &&
if [ -n $AuthSessionSecretLiteral ]; then grep -v '^AUTH_SESSION_SECRET=' .env > .env.tmp && printf 'AUTH_SESSION_SECRET=%s\n' $AuthSessionSecretLiteral >> .env.tmp && mv .env.tmp .env; fi &&
grep -v '^ESPN_SCOREBOARD_ENABLED=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_ENABLED=false\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_START_DATE=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_START_DATE=20260611\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_MAX_DAYS=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_MAX_DAYS=60\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_DAYS_BACK=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_DAYS_BACK=14\n' >> .env.tmp && mv .env.tmp .env &&
grep -v '^ESPN_SCOREBOARD_DAYS_FORWARD=' .env > .env.tmp && printf 'ESPN_SCOREBOARD_DAYS_FORWARD=14\n' >> .env.tmp && mv .env.tmp .env &&
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
if docker compose version >/dev/null 2>&1; then
  docker compose --env-file .env -f docker-compose.unraid.yml up -d --build;
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose --env-file .env -f docker-compose.unraid.yml up -d --build;
else
  echo 'Docker Compose is not installed on Unraid; falling back to plain docker build/run.' &&
  set -a && . ./.env && set +a &&
  docker network inspect wc2026-net >/dev/null 2>&1 || docker network create wc2026-net &&
  docker build -f backend/Dockerfile.unraid -t wc2026-backend:latest backend &&
  docker build -f frontend/Dockerfile.unraid -t wc2026-frontend:latest frontend &&
  (docker rm -f wc2026-frontend wc2026-backend >/dev/null 2>&1 || true) &&
  docker run -d --name wc2026-backend --restart unless-stopped --network wc2026-net --network-alias backend --env-file .env -e PORT=8000 -e DATABASE_URL=sqlite+aiosqlite:////app/data/wc2026.db -e MATCH_FEED_PATH=/app/data/matches.live.json -e MATCH_RESULTS_BACKFILL_PATH=/app/data/matches.public-results.json -e INJURY_FEED_PATH=/app/data/injuries.json -v '$UnraidPath/backend/data:/app/data' wc2026-backend:latest &&
  docker run -d --name wc2026-frontend --restart unless-stopped --network wc2026-net -p 0.0.0.0:${AppPort}:80 wc2026-frontend:latest;
fi
"@ -replace "`r?`n", " "

  Write-Host "Starting Docker deployment on Unraid..." -ForegroundColor Cyan
  & ssh -p $SshPort "${UnraidUser}@${UnraidHost}" $RemoteCommand
  if ($LASTEXITCODE -ne 0) {
    throw "Remote Docker deployment failed with exit code $LASTEXITCODE."
  }

  Write-Host "Done. Open http://$UnraidHost`:$AppPort/" -ForegroundColor Green
}
finally {
  Pop-Location
}
