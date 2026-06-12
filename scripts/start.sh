#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$INSTALL_DIR"

CONFIG_FILE="/opt/software/mallsenseai/mallsenseai.env"
[ -f "$CONFIG_FILE" ] && ln -sf "$CONFIG_FILE" .env

GREEN='\033[0;32m'; NC='\033[0m'
info() { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }

info "Starting MallSenseAI..."
docker compose up -d

info "Waiting for services..."
for i in $(seq 1 24); do
    if docker compose ps --format json 2>/dev/null | python3 -c "
import sys, json
services = [json.loads(l) for l in sys.stdin if l.strip()]
healthy = all(s.get('Health','') == 'healthy' or s.get('Status','') == 'running' for s in services)
sys.exit(0 if healthy else 1)
" 2>/dev/null; then
        HOST_PORT="$(grep -E '^HOST_PORT=' "$CONFIG_FILE" 2>/dev/null | cut -d= -f2 || echo 80)"
        info "All services running."
        info "  URL: http://localhost:${HOST_PORT:-80}"
        docker compose ps
        exit 0
    fi
    sleep 5
done

echo "Timeout. Current status:"
docker compose ps
docker compose logs --tail 20
exit 1
