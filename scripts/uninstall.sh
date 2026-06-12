#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${1:-/opt/module/mallsenseai}"
CONFIG_DIR="${CONFIG_DIR:-/opt/software/mallsenseai}"
DATA_DIR="${DATA_DIR:-/var/lib/mallsenseai}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*" >&2; }
die()   { printf "${RED}[FATAL]${NC} %s\n" "$*" >&2; exit 1; }

info "MallSenseAI Uninstaller"
info "======================="
info ""
warn "This will:"
warn "  1. Stop all MallSenseAI containers"
warn "  2. Remove containers and images"
warn "  3. Remove application files from $INSTALL_DIR"
warn ""
warn "Data preserved (not deleted):"
warn "  - Config: $CONFIG_DIR"
warn "  - Data:   $DATA_DIR"
warn ""

read -r -p "Continue? [y/N] " reply
[[ "$reply" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }

# ── Stop and remove containers ──
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    info "Stopping services..."
    cd "$INSTALL_DIR"
    docker compose down 2>/dev/null || true
fi

# ── Remove Docker images ──
info "Removing Docker images..."
docker images --filter "reference=mallsenseai*" -q | xargs -r docker rmi 2>/dev/null || true
docker image prune -f 2>/dev/null || true

# ── Remove application files ──
info "Removing application files..."
sudo rm -rf "$INSTALL_DIR"

info ""
info "MallSenseAI uninstalled."
info "Preserved data:"
info "  Config: $CONFIG_DIR/mallsenseai.env"
info "  Data:   $DATA_DIR/"
info ""
info "To remove all data: sudo rm -rf $CONFIG_DIR $DATA_DIR"
