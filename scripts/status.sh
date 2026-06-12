#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$INSTALL_DIR"

CONFIG_FILE="/opt/software/mallsenseai/mallsenseai.env"
DATA_DIR="${DATA_DIR:-/var/lib/mallsenseai}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MallSenseAI Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Docker services ──
echo "Services:"
if [ -f docker-compose.yml ]; then
    docker compose ps 2>/dev/null || echo "  No running services."
else
    echo "  Not installed in $INSTALL_DIR"
    exit 1
fi
echo ""

# ── Health check ──
HOST_PORT="$(grep -E '^HOST_PORT=' "$CONFIG_FILE" 2>/dev/null | cut -d= -f2 || echo 80)"
if curl -sSf "http://127.0.0.1:${HOST_PORT:-80}/api/health" >/dev/null 2>&1; then
    printf "  API Health: ${GREEN}OK${NC}\n"
else
    printf "  API Health: ${RED}UNREACHABLE${NC}\n"
fi
echo ""

# ── Disk usage ──
echo "Disk Usage:"
if [ -d "$DATA_DIR" ]; then
    echo "  Data:    $(du -sh "$DATA_DIR" 2>/dev/null | cut -f1 || echo 'N/A')"
fi
echo "  App:     $(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1 || echo 'N/A')"
echo ""

# ── Docker disk ──
echo "Docker:"
IMAGES="$(docker images --filter 'reference=*mallsenseai*' -q 2>/dev/null | wc -l)"
echo "  Images:  $IMAGES"
CONTAINERS="$(docker compose ps -q 2>/dev/null | wc -l)"
echo "  Running: $CONTAINERS containers"
echo ""

# ── URLs ──
echo "Endpoints:"
echo "  App:     http://localhost:${HOST_PORT:-80}"
echo "  API:     http://localhost:${HOST_PORT:-80}/api/health"
echo "  Swagger: http://localhost:${HOST_PORT:-80}/docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
