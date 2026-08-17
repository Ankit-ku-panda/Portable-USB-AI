#!/bin/bash

# PortableAI Setup Script for Linux and macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "===================================="
echo "   PORTABLEAI SETUP WIZARD"
echo "===================================="
echo -e "${NC}"

# Detect Python
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo -e "${RED}ERROR: Python 3 is required but not found.${NC}"
    echo "Please install Python 3 and try again."
    read -p "Press Enter to exit..."
    exit 1
fi

echo -e "${GREEN}✓ Python found: $($PY_CMD --version)${NC}"
echo

# Create necessary directories
mkdir -p models
mkdir -p data/chats
mkdir -p installer_data

echo -e "${GREEN}✓ Directories created${NC}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# PortableAI Configuration
CONTEXT_SIZE=4096
MAX_TOKENS=256
TEMPERATURE=0.1
PORT=9000
LLAMA_PORT=8080
EOF
    echo -e "${GREEN}✓ Configuration file created (.env)${NC}"
else
    echo -e "${YELLOW}⚠ Configuration file exists (skipping)${NC}"
fi

echo

# Count existing models
model_count=0
if [ -d "models" ]; then
    model_count=$(find models -maxdepth 1 -name "*.gguf" 2>/dev/null | wc -l)
fi

if [ $model_count -gt 0 ]; then
    echo -e "${BLUE}Found $model_count existing model(s):${NC}"
    ls -lh models/*.gguf 2>/dev/null
    echo
fi

# Setup menu
while true; do
    clear
    echo -e "${BLUE}"
    echo "===================================="
    echo "   PORTABLEAI SETUP"
    echo "===================================="
    echo -e "${NC}"
    echo
    echo "1) Start PortableAI (use existing models)"
    echo "2) Download Qwen 3 4B (recommended - lightweight)"
    echo "3) Enter custom HuggingFace model URL"
    echo "4) View installed models"
    echo "5) Exit setup"
    echo
    read -p "Choose an option [1-5]: " setup_choice

    case $setup_choice in
        1) break ;;
        2)
            model_url="https://huggingface.co/Qwen/Qwen3-4B-Instruct-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf"
            model_name="Qwen3-4B-Q4_K_M.gguf"
            download_model "$model_url" "$model_name"
            ;;
        3)
            clear
            echo
            read -p "Paste HuggingFace model URL: " model_url
            if [ -z "$model_url" ]; then
                echo "Cancelled."
                sleep 2
                continue
            fi
            model_name=$(basename "$model_url" | sed 's/?.*$//')
            [ -z "$model_name" ] && model_name="custom-model.gguf"
            download_model "$model_url" "$model_name"
            ;;
        4)
            clear
            echo
            echo -e "${BLUE}===================================="
            echo "   INSTALLED MODELS"
            echo "====================================${NC}"
            echo
            if [ -d "models" ]; then
                find models -maxdepth 1 -name "*.gguf" -exec ls -lh {} \; || echo "No models found."
            else
                echo "Models directory not found."
            fi
            echo
            read -p "Press Enter to continue..."
            ;;
        5)
            echo
            echo "Setup complete. Run ./start.sh to start PortableAI."
            echo
            exit 0
            ;;
        *)
            echo "Invalid option."
            sleep 2
            ;;
    esac
done

# Start the app
clear
echo
echo -e "${BLUE}===================================="
echo "   STARTING PORTABLEAI"
echo "====================================${NC}"
echo
echo "To access PortableAI:"
echo "  Web UI: http://127.0.0.1:9000"
echo
echo "Keep this terminal open while using PortableAI."
echo "Press Ctrl+C to stop the server."
echo
sleep 3

bash start.sh
exit 0

# Download model function
download_model() {
    local url="$1"
    local name="$2"

    if [ -f "models/$name" ]; then
        echo
        echo -e "${YELLOW}⚠ Model already exists: models/$name${NC}"
        echo
        read -p "Press Enter to continue..."
        return
    fi

    clear
    echo
    echo -e "${BLUE}Downloading $name...${NC}"
    echo "This model is optimized for speed and efficiency."
    echo
    echo "Note: Large models can take 30+ minutes."
    echo "Do NOT close this window."
    echo

    $PY_CMD << PYTHON
import urllib.request
import os

url = r'$url'
file_path = os.path.join('models', r'$name')

def show_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(100, int(100 * downloaded / total_size))
    print(f'\rProgress: {percent}%', end='', flush=True)

try:
    print(f'Downloading from: {url}')
    print(f'Saving to: {file_path}')
    urllib.request.urlretrieve(url, file_path, reporthook=show_progress)
    print('\n✓ Download complete!')
except Exception as e:
    print(f'\n✗ Error: {e}')
    exit(1)
PYTHON

    if [ $? -eq 0 ]; then
        echo
        echo -e "${GREEN}✓ Model downloaded successfully!${NC}"
        echo
        read -p "Press Enter to continue..."
    else
        echo
        echo -e "${RED}✗ Download failed. Check your internet connection.${NC}"
        echo
        read -p "Press Enter to continue..."
    fi
}
