# Build and run the Avatar container (Windows).
# Stops any existing container, rebuilds the image, runs with the root .env.
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Remove an existing container only if one exists (avoids a stderr message
# that PowerShell 5.1 would otherwise promote to a terminating error).
$existing = docker ps -aq --filter "name=^avatar$"
if ($existing) { docker rm -f avatar | Out-Null }

docker build -t avatar .
if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }
docker run -d --name avatar --env-file .env -p 8000:8000 avatar
if ($LASTEXITCODE -ne 0) { Write-Error "Docker run failed"; exit 1 }
Write-Host "Avatar running at http://localhost:8000  (admin at /admin)"
