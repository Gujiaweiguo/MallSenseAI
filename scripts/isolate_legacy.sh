#!/usr/bin/env bash
# Legacy isolation script for MallSenseAI platform migration.
# Copies legacy Python files to legacy/ directory without deleting originals.
# Idempotent — safe to run multiple times.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LEGACY_DIR="$PROJECT_ROOT/legacy"

echo "=== MallSenseAI Legacy Isolation ==="
echo "Project root: $PROJECT_ROOT"
echo "Legacy dir:   $LEGACY_DIR"
echo ""

# Create legacy directory
mkdir -p "$LEGACY_DIR"

# Files to copy to legacy/
LEGACY_FILES=(
    "blue_box_detector.py"
    "convert_coordinates.py"
    "debug_image_compare.py"
)

for file in "${LEGACY_FILES[@]}"; do
    src="$PROJECT_ROOT/$file"
    dest="$LEGACY_DIR/$file"
    if [ -f "$src" ]; then
        if [ -f "$dest" ]; then
            echo "  [skip] $file (already in legacy/)"
        else
            cp "$src" "$dest"
            echo "  [copy] $file -> legacy/$file"
        fi
    else
        echo "  [warn] $file not found in root, skipping"
    fi
done

# Copy root-level safe_zones.json (stale template)
if [ -f "$PROJECT_ROOT/safe_zones.json" ]; then
    if [ ! -f "$LEGACY_DIR/safe_zones.json" ]; then
        cp "$PROJECT_ROOT/safe_zones.json" "$LEGACY_DIR/safe_zones.json"
        echo "  [copy] safe_zones.json -> legacy/safe_zones.json"
    else
        echo "  [skip] safe_zones.json (already in legacy/)"
    fi
fi

echo ""
echo "=== Shared assets remaining in root ==="
echo "  alarm_images/  — production data (cameras, baselines, ROIs, logs)"
echo "  camera_configs.json — legacy camera config (migration input)"
echo "  config.py — legacy alarm config (migration input)"
echo "  yolov8*.pt — YOLO model weights"
echo "  requirements.txt — legacy dependency manifest"
echo ""
echo "=== Done. Root files are preserved. ==="
