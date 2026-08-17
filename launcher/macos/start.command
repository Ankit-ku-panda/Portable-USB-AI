#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

show_menu() {
  echo "===================================="
  echo "   PORTABLEAI LAUNCHER"
  echo "===================================="
  echo
  echo "Current setup:"
  if [ -f config.json ]; then
    provider=$(python3 - <<'PY'
import json
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print((data.get('provider') or 'local').strip())
except Exception:
    print('local')
PY
)
    model=$(python3 - <<'PY'
import json
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    model = data.get('model') or ''
    print(model if model else 'auto-detect')
except Exception:
    print('auto-detect')
PY
)
    echo "  Provider: $provider"
    echo "  Model: $model"
  else
    echo "  Provider: local"
    echo "  Model: auto-detect"
  fi
  echo
  echo "1) PortableAI Custom UI"
  echo "2) llama.cpp Built-in UI"
  echo "3) Start local GGUF model (shared llama-server)"
  echo "4) Start with OpenAI"
  echo "5) Start with Gemini"
  echo "6) Start with DeepSeek"
  echo "7) Start with OpenRouter"
  echo "8) Start with custom endpoint"
  echo "9) Exit"
  echo
}

start_local() {
  echo
  echo "Available GGUF models:"
  for model in models/*.gguf 2>/dev/null; do
    [ -f "$model" ] && echo "  - $(basename "$model")"
  done

  echo
  read -p "Enter model filename or press Enter for auto-select: " selected_model

  if [ -n "$selected_model" ] && [ -f "models/$selected_model" ]; then
    "$PYTHON_BIN" app/server.py "$selected_model" local
  else
    if [ -n "$selected_model" ]; then
      echo "Model not found: $selected_model"
      echo "Falling back to the default local model..."
    fi
    "$PYTHON_BIN" app/server.py "" local
  fi
}

start_remote() {
  provider="$1"
  echo
  read -p "Model name: " selected_model
  selected_model="${selected_model:-gpt-4o-mini}"

  echo
  read -s -p "API key: " api_key
  echo

  case "$provider" in
    openai) base_url="https://api.openai.com/v1" ;;
    gemini) base_url="https://generativelanguage.googleapis.com/v1beta/openai" ;;
    deepseek) base_url="https://api.deepseek.com/v1" ;;
    openrouter) base_url="https://openrouter.ai/api/v1" ;;
    custom)
      read -p "Base URL (example: https://your-endpoint/v1): " base_url
      base_url="${base_url:-https://api.openai.com/v1}"
      ;;
    *) base_url="https://api.openai.com/v1" ;;
  esac

  echo
  echo "Starting PortableAI with provider: $provider"
  echo "Model: $selected_model"
  echo "Base URL: $base_url"
  echo
  "$PYTHON_BIN" app/server.py "$selected_model" "$provider" "$api_key" "$base_url"
}

while true; do
  clear
  show_menu
  read -p "Choose an option [1-9]: " choice

  case "$choice" in
    1) echo "Opening PortableAI Custom UI: http://127.0.0.1:9000"; if command -v open >/dev/null 2>&1; then open http://127.0.0.1:9000; else echo "Open http://127.0.0.1:9000 in your browser."; fi; read -p "Press Enter to return to the menu..." _; ;;
    2) echo "Opening llama.cpp Built-in UI: http://127.0.0.1:8080"; if command -v open >/dev/null 2>&1; then open http://127.0.0.1:8080; else echo "Open http://127.0.0.1:8080 in your browser."; fi; read -p "Press Enter to return to the menu..." _; ;;
    3) start_local; break ;;
    4) start_remote openai ; break ;;
    5) start_remote gemini ; break ;;
    6) start_remote deepseek ; break ;;
    7) start_remote openrouter ; break ;;
    8) start_remote custom ; break ;;
    9) echo "Goodbye."; exit 0 ;;
    *) echo "Invalid option. Press Enter to continue..."; read -p "" _ ;;
  esac

done
