#!/usr/bin/env python3
"""
PortableAI - Simplified Server
Manages llama-server process and handles graceful shutdown.
All UI interaction happens through llama-server's built-in UI.
"""

from pathlib import Path
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
import os
import platform
import signal

# ============================================================
# LOAD ENVIRONMENT VARIABLES FROM .env
# ============================================================

def load_env_file():
    """Load .env file manually without external dependencies."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not key.startswith("#"):
                            os.environ.setdefault(key, value)
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

load_env_file()

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
CONFIG_DIR = ROOT / "config"

LLAMA_PORT = int(os.getenv("LLAMA_PORT", 8080))
CONFIG_PATH = CONFIG_DIR / "config.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LLAMA.CPP EXECUTABLE
# ============================================================

OS_TYPE = platform.system()

if OS_TYPE == "Windows":
    LLAMA = ROOT / "app" / "llama" / "llama-server.exe"
elif OS_TYPE == "Darwin":
    LLAMA = ROOT / "app" / "llama" / "llama-server"
else:
    LLAMA = ROOT / "app" / "llama" / "llama-server"

# ============================================================
# FIND AVAILABLE MODELS
# ============================================================

def get_models():
    """Return all GGUF models in the models directory."""
    MODELS.mkdir(parents=True, exist_ok=True)
    return sorted(
        MODELS.glob("*.gguf"),
        key=lambda p: p.name.lower()
    )


def find_model():
    """Find the best available model."""
    models = get_models()

    if not models:
        print()
        print("ERROR: No GGUF model found.")
        print()
        print(f"Put a .gguf model inside:")
        print(MODELS)
        print()
        sys.exit(1)

    # Prefer Qwen3 4B if present
    preferred_names = [
        "qwen3-4b-q4_k_m.gguf",
        "qwen3-4b-q4_k_m",
        "qwen3-4b",
    ]

    for model in models:
        filename = model.name.lower()
        for preferred in preferred_names:
            if filename == preferred.lower():
                return model

    # Otherwise prefer any model containing "qwen"
    qwen_models = [
        model for model in models
        if "qwen" in model.name.lower()
    ]
    if qwen_models:
        return qwen_models[0]

    # Otherwise use first GGUF
    return models[0]


# ============================================================
# GPU DETECTION
# ============================================================

def detect_gpu_layers():
    """Detect optimal GPU layers based on available hardware."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            vram_mb = int(result.stdout.strip())
            vram_gb = vram_mb / 1024
            print(f"Detected GPU VRAM: {vram_gb:.1f} GB")
            
            # Conservative GPU layer allocation
            if vram_gb >= 12:
                return -1
            elif vram_gb >= 8:
                return 30
            elif vram_gb >= 6:
                return 24
            elif vram_gb >= 4:
                return 20
            else:
                return 0
    except Exception as e:
        print(f"GPU detection failed: {e}")
    
    return 0


# ============================================================
# START LLAMA.CPP
# ============================================================

def start_llama(model):
    """Start llama-server process."""
    
    # Load config for GPU layers setting
    config = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except:
            pass
    
    gpu_layers_config = config.get("gpu_layers", "auto")
    
    if gpu_layers_config == "auto":
        gpu_layers = detect_gpu_layers()
    else:
        try:
            gpu_layers = int(gpu_layers_config)
        except (ValueError, TypeError):
            gpu_layers = 0

    # Allow environment variable override
    try:
        env_gpu_layers = int(os.environ.get("PORTABLEAI_GPU_LAYERS", str(gpu_layers)))
        gpu_layers = env_gpu_layers
    except ValueError:
        pass

    print(f"Using GPU layers: {gpu_layers}")

    command = [
        str(LLAMA),
        "-m", str(model),
        "-c", "4096",      # Context size
        "-ngl", str(gpu_layers),  # GPU layers
        "-b", "512",       # Batch size
        "-ub", "256",      # Ubatch size
        "-t", "8",         # Threads
        "-tb", "8",        # Thread batch
        "--host", "127.0.0.1",
        "--port", str(LLAMA_PORT)
    ]

    print()
    print("=" * 60)
    print("STARTING LLAMA.CPP")
    print("=" * 60)
    print(f"Model: {model.name}")
    print(f"GPU layers: {gpu_layers}")
    print(f"Command: {' '.join(command)}")
    print("=" * 60)
    print()

    process = subprocess.Popen(command, stdout=None, stderr=None)
    return process


# ============================================================
# WAIT FOR LLAMA SERVER
# ============================================================

def wait_for_llama(timeout=60):
    """Wait for llama-server to be ready."""
    print("Waiting for llama.cpp...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            request = urllib.request.urlopen(
                f"http://127.0.0.1:{LLAMA_PORT}/health",
                timeout=2
            )
            if request.status == 200:
                print("llama.cpp is ready.")
                return True
        except Exception:
            pass
        time.sleep(1)

    print()
    print(f"WARNING: llama.cpp did not become ready within {timeout} seconds.")
    print()
    return False


# ============================================================
# MAIN
# ============================================================

llama_process = None

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global llama_process
    print()
    print("Shutting down PortableAI...")
    
    if llama_process is not None:
        try:
            llama_process.terminate()
            llama_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            llama_process.kill()
    
    sys.exit(0)


def main():
    global llama_process
    
    print("=" * 60)
    print("PORTABLE LOCAL AI")
    print("=" * 60)
    print()

    # Check llama executable exists
    if not LLAMA.exists():
        print("ERROR: llama-server not found:")
        print(LLAMA)
        sys.exit(1)

    # Find and start model
    model = find_model()
    print(f"Model selected: {model.name}")
    print()

    # Start llama-server
    llama_process = start_llama(model)

    # Wait for readiness
    if not wait_for_llama(60):
        print("ERROR: llama.cpp failed to start")
        if llama_process:
            llama_process.kill()
        sys.exit(1)

    # Print status
    print()
    print("=" * 60)
    print("PORTABLE AI READY")
    print("=" * 60)
    print()
    print(f"llama.cpp Web UI: http://127.0.0.1:{LLAMA_PORT}")
    print()
    print("Opening your browser...")
    print()

    # Try to open browser (optional)
    try:
        if platform.system() == "Darwin":
            os.system(f"open http://127.0.0.1:{LLAMA_PORT}")
        elif platform.system() == "Windows":
            os.system(f"start http://127.0.0.1:{LLAMA_PORT}")
        else:
            os.system(f"xdg-open http://127.0.0.1:{LLAMA_PORT} 2>/dev/null || true")
    except:
        pass

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep running
    try:
        while True:
            time.sleep(1)
            if llama_process.poll() is not None:
                print("llama.cpp process died unexpectedly!")
                sys.exit(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
