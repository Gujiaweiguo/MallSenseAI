#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default paths
INSTALL_DIR="${1:-/opt/module/mallsenseai}"
CONFIG_DIR="${CONFIG_DIR:-/opt/software/mallsenseai}"
DATA_DIR="${DATA_DIR:-/var/lib/mallsenseai}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*" >&2; }
die()   { printf "${RED}[FATAL]${NC} %s\n" "$*" >&2; exit 1; }

# ── Pre-flight checks ──
info "MallSenseAI Installer"
info "====================="
info ""

command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker first."
docker compose version >/dev/null 2>&1 || die "'docker compose' plugin not found."
command -v curl >/dev/null 2>&1 || die "curl is required."
command -v openssl >/dev/null 2>&1 || die "openssl is required."
docker info >/dev/null 2>&1 || die "Docker daemon is not running."

info "Pre-flight checks passed."

# ── Create directories ──
info "Creating directories..."
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$CONFIG_DIR"
sudo mkdir -p "$DATA_DIR"/{postgres,assets}

# ── Copy application files ──
info "Installing application files to $INSTALL_DIR ..."
sudo cp "$PROJECT_DIR"/Dockerfile "$INSTALL_DIR/"
sudo cp "$PROJECT_DIR"/docker-compose.yml "$INSTALL_DIR/"
sudo cp "$PROJECT_DIR"/nginx.conf "$INSTALL_DIR/"
sudo cp "$PROJECT_DIR"/.dockerignore "$INSTALL_DIR/" 2>/dev/null || true
sudo cp -r "$PROJECT_DIR"/backend "$INSTALL_DIR/"
sudo cp -r "$PROJECT_DIR"/workers "$INSTALL_DIR/"
sudo cp -r "$PROJECT_DIR"/shared "$INSTALL_DIR/"

# ── Build frontend ──
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    sudo mkdir -p "$INSTALL_DIR/frontend"
    sudo cp -r "$PROJECT_DIR/frontend/dist" "$INSTALL_DIR/frontend/"
    info "Frontend build copied."
else
    warn "frontend/dist not found. Building frontend..."
    (cd "$PROJECT_DIR/frontend" && npm ci && npm run build) || die "Frontend build failed."
    sudo mkdir -p "$INSTALL_DIR/frontend"
    sudo cp -r "$PROJECT_DIR/frontend/dist" "$INSTALL_DIR/frontend/"
    info "Frontend built and copied."
fi

# ── Configuration ──
CONFIG_FILE="$CONFIG_DIR/mallsenseai.env"
if [ ! -f "$CONFIG_FILE" ]; then
    info "Generating configuration..."
    sudo cp "$PROJECT_DIR/deploy/mallsenseai.env.example" "$CONFIG_FILE"
    sudo chown "$(id -u):$(id -g)" "$CONFIG_FILE"

    # Generate random secrets
    SECRET_KEY="$(openssl rand -hex 32)"
    POSTGRES_PASSWORD="$(openssl rand -hex 16)"

    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$CONFIG_FILE"
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" "$CONFIG_FILE"

    chmod 600 "$CONFIG_FILE"
    info "Configuration written to $CONFIG_FILE"
    info "  Postgres user: mallsenseai"
    info "  Postgres password: $POSTGRES_PASSWORD"
    info "  Secret key: generated (32 bytes)"
    warn "Save these credentials! Edit $CONFIG_FILE to customize."
else
    info "Existing configuration found at $CONFIG_FILE — preserving."
fi

# ── Create .env symlink in install dir ──
ln -sf "$CONFIG_FILE" "$INSTALL_DIR/.env"

# ── Fix ownership ──
sudo chown -R "$(id -u):$(id -g)" "$INSTALL_DIR"
sudo chown -R "$(id -u):$(id -g)" "$DATA_DIR"

# ── Build Docker image ──
info "Building Docker image (this may take a few minutes)..."
cd "$INSTALL_DIR"
docker compose build --quiet 2>&1 || die "Docker build failed."

# ── Start services ──
info "Starting services..."
docker compose up -d

# ── Wait for PostgreSQL ──
info "Waiting for database..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U mallsenseai >/dev/null 2>&1; then
        info "Database is ready."
        break
    fi
    sleep 2
done

# ── Run database migrations ──
info "Running database migrations..."
docker compose exec -T backend python -m alembic -c backend/app/db/alembic.ini upgrade head 2>&1 || warn "Migration may have already been applied."

# ── Seed admin user ──
info "Seeding default admin user (admin/admin123)..."
docker compose exec -T backend python -c "from backend.app.db.seed import seed_default_admin; seed_default_admin()" 2>&1 || warn "Admin user may already exist."

# ── Wait for healthy ──
HOST_PORT="$(grep -E '^HOST_PORT=' "$CONFIG_FILE" 2>/dev/null | cut -d= -f2)"
HOST_PORT="${HOST_PORT:-80}"

info "Waiting for services to become healthy (up to 120s)..."
for i in $(seq 1 24); do
    if curl -sSf "http://127.0.0.1:${HOST_PORT}/api/health" >/dev/null 2>&1; then
        info ""
        info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        info "  MallSenseAI installed successfully!"
        info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        info "  URL:      http://localhost:${HOST_PORT}"
        info "  Login:    admin / admin123"
        info "  Config:   $CONFIG_FILE"
        info "  Data:     $DATA_DIR"
        info "  Install:  $INSTALL_DIR"
        info ""
        info "  Commands:"
        info "    cd $INSTALL_DIR && docker compose ps       # Status"
        info "    cd $INSTALL_DIR && docker compose logs -f   # Logs"
        info "    cd $INSTALL_DIR && docker compose down       # Stop"
        info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 0
    fi
    sleep 5
done

warn "Services did not become healthy within 120s."
warn "Check logs: cd $INSTALL_DIR && docker compose logs -f"
exit 1
