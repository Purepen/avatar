#!/usr/bin/env bash
# Build and run the Avatar container (macOS/Linux).
# Stops any existing container, rebuilds the image, runs with the root .env.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker rm -f avatar 2>/dev/null || true
docker build -t avatar .
docker run -d --name avatar --env-file .env -p 8000:8000 avatar
echo "Avatar running at http://localhost:8000  (admin at /admin)"
