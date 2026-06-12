#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${1:-/opt/module/mallsenseai}"
DATA_DIR="${DATA_DIR:-/var/lib/mallsenseai}"
BACKUP_DIR="${DATA_DIR}/backups"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$INSTALL_DIR"

info "MallSenseAI Update"
info "=================="

# ── Backup database ──
info "Backing up database..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/mallsenseai_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose exec -T postgres pg_dump -U mallsenseai mallsenseai | gzip > "$BACKUP_FILE"
info "Backup saved: $BACKUP_FILE"

# ── Copy new files ──
info "Updating application files..."
cp "$PROJECT_DIR"/Dockerfile "$INSTALL_DIR/"
cp "$PROJECT_DIR"/docker-compose.yml "$INSTALL_DIR/"
cp "$PROJECT_DIR"/nginx.conf "$INSTALL_DIR/"
cp -r "$PROJECT_DIR"/backend "$INSTALL_DIR/"
cp -r "$PROJECT_DIR"/workers "$INSTALL_DIR/"
cp -r "$PROJECT_DIR"/shared "$INSTALL_DIR/"

# ── Rebuild frontend if needed ──
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    cp -r "$PROJECT_DIR/frontend/dist" "$INSTALL_DIR/frontend/"
else
    warn "No frontend/dist found. Run 'cd frontend && npm run build' first."
fi

# ── Rebuild image ──
info "Rebuilding Docker image..."
docker compose build --quiet

# ── Restart with new image ──
info "Restarting services..."
docker compose up -d

# ── Run migrations ──
info "Running database migrations..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U mallsenseai >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
docker compose exec -T backend python -m alembic -c backend/app/db/alembic.ini upgrade head 2>&1 || warn "Migration issue — check logs."

# ── Wait for healthy ──
CONFIG_FILE="/opt/software/mallsenseai/mallsenseai.env"
HOST_PORT="$(grep -E '^HOST_PORT=' "$CONFIG_FILE" 2>/dev/null | cut -d= -f2 || echo 80)"

info "Waiting for services..."
for i in $(seq 1 24); do
    if curl -sSf "http://127.0.0.1:${HOST_PORT:-80}/api/health" >/dev/null 2>&1; then
        info "Update complete! Services healthy."
        docker compose ps
        exit 0
    fi
    sleep 5
done

warn "Services not healthy after 120s. Check: docker compose logs -f"
exit 1
