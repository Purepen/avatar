# Stop and remove the Avatar container (Windows).
$existing = docker ps -aq --filter "name=^avatar$"
if ($existing) { docker rm -f avatar | Out-Null }
Write-Host "Avatar container stopped."
