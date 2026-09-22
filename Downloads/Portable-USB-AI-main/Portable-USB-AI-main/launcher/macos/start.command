#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# ========================================================
# AUTO-CACHE CLEARING FOR PORTABILITY
# ========================================================
# Clear old path caches so the app works on different Macs

if [ -d "app/__pycache__" ]; then
    echo "Clearing Python cache..."
    rm -rf "app/__pycache__"
fi

# ========================================================
# LOAD ENVIRONMENT CONFIGURATION
# ========================================================

if [ -f ".env" ]; then
    set -a
    source ".env"
    set +a
fi

# ========================================================
# PYTHON DETECTION
# ========================================================

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required to run PortableAI."
  read -p "Press Enter to exit..." _
  exit 1
fi

# ========================================================
# START LLAMA.CPP WITH BUILT-IN UI
# ========================================================

clear
echo "===================================="
echo "   PORTABLE LOCAL AI"
echo "===================================="
echo
echo "Starting llama.cpp server with built-in UI..."
echo

"$PYTHON_BIN" app/server.py

# If we get here, the server exited
echo
echo "Server stopped."
