#!/usr/bin/env bash
# Stop and remove the Avatar container (macOS/Linux).
docker rm -f avatar 2>/dev/null || true
echo "Avatar container stopped."
