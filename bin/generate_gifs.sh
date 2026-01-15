#!/bin/bash
# Generate GIFs from VHS tape files in docs/static/
# Requires VHS: https://github.com/charmbracelet/vhs
#
# Usage:
#   ./bin/generate_gifs.sh              # Generate all GIFs
#   ./bin/generate_gifs.sh tui-demo     # Generate specific GIF

set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

TAPES_DIR="docs/static"

# Check if VHS is installed
if ! command -v vhs &> /dev/null; then
    echo "Error: VHS is not installed."
    echo "Install from: https://github.com/charmbracelet/vhs#installation"
    exit 1
fi

if [ $# -eq 0 ]; then
    # Generate all GIFs
    for tape in "$TAPES_DIR"/*.tape; do
        if [ -f "$tape" ]; then
            echo "Recording $(basename "$tape" .tape)..."
            vhs "$tape"
        fi
    done
else
    # Generate specific GIF
    tape="$TAPES_DIR/$1.tape"
    if [ -f "$tape" ]; then
        echo "Recording $1..."
        vhs "$tape"
    else
        echo "Error: Tape file not found: $tape"
        echo "Available tapes:"
        ls -1 "$TAPES_DIR"/*.tape 2>/dev/null | xargs -I{} basename {} .tape | sed 's/^/  /'
        exit 1
    fi
fi

echo "Done!"