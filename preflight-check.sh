#!/bin/bash

# PortableAI Preflight Check for Linux

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "===================================="
echo "   PORTABLEAI PREFLIGHT CHECK"
echo "===================================="
echo -e "${NC}"
echo

# Check if running from USB or portable location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${BLUE}Location: $SCRIPT_DIR${NC}"
echo

# Check Python
echo "Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$($command python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python 3 found: $PY_VERSION${NC}"
elif command -v python >/dev/null 2>&1; then
    PY_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python found: $PY_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3 is required but not found.${NC}"
    echo "  Install it using: sudo apt-get install python3 (Ubuntu/Debian)"
    echo "                    sudo yum install python3 (CentOS/RHEL)"
    echo "  Or download from: https://python.org"
    exit 1
fi
echo

# Check disk space
echo "Checking disk space..."
available_space=$(df "$SCRIPT_DIR" | tail -1 | awk '{print $4}')
available_gb=$((available_space / 1024 / 1024))
if [ $available_gb -lt 10 ]; then
    echo -e "${YELLOW}⚠ Warning: Only ${available_gb}GB available.${NC}"
    echo "  Models can be 5-15GB. Ensure sufficient space."
else
    echo -e "${GREEN}✓ Sufficient disk space available (${available_gb}GB)${NC}"
fi
echo

# Check write permissions
echo "Checking write permissions..."
if [ -w "$SCRIPT_DIR" ]; then
    echo -e "${GREEN}✓ Write permissions OK${NC}"
else
    echo -e "${RED}✗ No write permissions in: $SCRIPT_DIR${NC}"
    echo "  Run with appropriate permissions or change directory."
    exit 1
fi
echo

# Check internet connectivity
echo "Checking internet connectivity..."
if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1 || ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Internet connection available${NC}"
else
    echo -e "${YELLOW}⚠ No internet detected. Models won't be downloadable.${NC}"
fi
echo

# Summary
echo -e "${BLUE}===================================="
echo "   PREFLIGHT CHECK COMPLETE"
echo "====================================${NC}"
echo
echo "Next steps:"
echo "  1. Make the install script executable:"
echo "     chmod +x install.sh"
echo "  2. Run the installer:"
echo "     bash install.sh"
echo
read -p "Press Enter to run the installer now... " -t 5

cd "$SCRIPT_DIR"
bash install.sh
