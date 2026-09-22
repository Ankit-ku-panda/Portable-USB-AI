from pathlib import Path
import subprocess
import time
import urllib.request
import webbrowser


# Project folders
ROOT = Path(__file__).resolve().parent.parent
MODEL_FOLDER = ROOT / "models"
LLAMA_SERVER = ROOT / "app" / "llama" / "llama-server.exe"

PORT = 8080


def find_model():
    """Find the first GGUF model inside the models folder."""

    models = list(MODEL_FOLDER.glob("*.gguf"))

    if not models:
        print("No GGUF model found.")
        return None

    return models[0]


def start_server(model):
    """Start llama.cpp server with the selected model."""

    command = [
        str(LLAMA_SERVER),
        "-m", str(model),
        "-c", "4096",
        "-ngl", "20",
        "--host", "127.0.0.1",
        "--port", str(PORT)
    ]

    print("Starting AI model...")
    return subprocess.Popen(command)


def wait_for_server():
    """Wait until llama.cpp is ready."""

    url = f"http://127.0.0.1:{PORT}/health"

    for i in range(60):
        try:
            response = urllib.request.urlopen(url, timeout=2)

            if response.status == 200:
                return True

        except:
            pass

        time.sleep(1)

    return False


def main():

    print("Portable Local AI")

    # Check llama-server
    if not LLAMA_SERVER.exists():
        print("llama-server.exe not found.")
        return

    # Find model
    model = find_model()

    if model is None:
        return

    print("Model:", model.name)

    # Start llama.cpp
    process = start_server(model)

    # Wait until server starts
    if wait_for_server():

        url = f"http://127.0.0.1:{PORT}"

        print("AI is ready.")
        print("Open:", url)

        webbrowser.open(url)

    else:
        print("Server failed to start.")
        process.terminate()
        return

    # Keep Python running
    try:
        process.wait()

    except KeyboardInterrupt:
        print("\nStopping AI...")
        process.terminate()


if __name__ == "__main__":
    main()
