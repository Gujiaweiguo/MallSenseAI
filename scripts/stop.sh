#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$INSTALL_DIR"

GREEN='\033[0;32m'; NC='\033[0m'
info() { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }

info "Stopping MallSenseAI..."
docker compose down
info "Services stopped. Data preserved."
