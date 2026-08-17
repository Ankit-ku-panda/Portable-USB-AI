from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
import json
import urllib.request
import urllib.error
import os
from datetime import datetime
import platform

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
WEB = ROOT / "app" / "web"
CHATS = ROOT / "data" / "chats"

PORT = int(os.getenv("PORT", 9000))
LLAMA_PORT = int(os.getenv("LLAMA_PORT", 8080))
CONFIG_PATH = ROOT / "config.json"

CHATS.mkdir(parents=True, exist_ok=True)

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
# CONFIGURATION
# ============================================================

def default_base_url_for_provider(provider_name):
    provider = (provider_name or "local").strip().lower()
    defaults = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        "custom": "https://api.openai.com/v1",
    }
    return defaults.get(provider, "")


def normalize_base_url(provider_name, base_url):
    raw = (base_url or "").strip()
    if not raw:
        return default_base_url_for_provider(provider_name)

    raw = raw.rstrip("/")
    if raw.endswith("/chat/completions"):
        raw = raw.rsplit("/chat/completions", 1)[0]

    provider = (provider_name or "local").strip().lower()

    if provider == "gemini":
        if "/v1beta" in raw or "/openai" in raw:
            return raw
        return f"{raw}/v1beta/openai"

    if provider in {"openai", "openrouter", "deepseek", "custom"}:
        if raw.endswith("/v1"):
            return raw
        if raw.endswith("/chat/completions"):
            return raw.rsplit("/chat/completions", 1)[0]
        return f"{raw}/v1"

    return raw


def load_config():
    default_config = {
        "provider": "local",
        "model": "",
        "base_url": "",
        "api_key": "",
        "context_size": int(os.getenv("CONTEXT_SIZE", 4096)),
        "threads": 8,
        "gpu_layers": "auto",
        "port": PORT,
        "llama_port": LLAMA_PORT,
        "temperature": float(os.getenv("TEMPERATURE", 0.1)),
        "max_tokens": int(os.getenv("MAX_TOKENS", 256)),
        "top_p": 0.9,
        "repeat_penalty": 1.1
    }

    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if isinstance(imported, dict):
                default_config.update(imported)
    except Exception as e:
        print(f"Config warning: {e}")

    return default_config


server_config = load_config()

SYSTEM_PROMPT = """You are PortableAI, a precise coding and reasoning assistant focused on correctness.

## CORE PRINCIPLES
- Always prioritize correctness over speed or length.
- Produce code that is runnable, valid, and free of obvious logic bugs.
- Think through edge cases before answering.
- Prefer standard-library, idiomatic solutions unless the user requests otherwise.
- If something is ambiguous, state the assumption clearly.

## CODING STANDARDS
- Deliver complete, runnable code examples.
- Include necessary imports, function signatures, and error handling.
- Avoid hallucinated APIs or unsupported libraries.
- Use clear naming and keep logic simple and correct.
- For algorithmic tasks, check edge cases like empty inputs, zero values, negative numbers, and boundary conditions.
- If a user asks for a fix, provide the corrected code and explain the issue briefly.

## CODE RESPONSE FORMAT
```python
# correct, runnable example
```
- Always specify the programming language.
- Keep code concise but complete.
- Add short comments only when helpful.

## REASONING PROCESS
1. Understand the exact requirement.
2. Consider edge cases and invalid input.
3. Choose the simplest correct solution.
4. Validate the logic mentally before responding.
5. Output the final answer in a clean, correct format.

## BEST PRACTICES
- Keep the explanation brief and focused.
- Explain what the function does and why it is correct.
- If an answer might be uncertain, say so and include the safest version.

You are PortableAI - a local AI assistant optimized for reliable coding and reasoning."""


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


# ============================================================
# SELECT DEFAULT MODEL
# ============================================================

def resolve_model_name(requested_name=""):
    """Resolve a model name or path to the actual GGUF file."""

    if not requested_name:
        return find_model()

    requested_name = requested_name.strip()

    if not requested_name:
        return find_model()

    candidates = get_models()
    candidate_strings = [str(model).lower() for model in candidates]

    if os.path.isabs(requested_name) or "/" in requested_name or "\\" in requested_name:
        requested_path = Path(requested_name).expanduser()
        if requested_path.exists() and requested_path.suffix.lower() == ".gguf":
            return requested_path.resolve()

        for model in candidates:
            if str(model).lower() == str(requested_path).lower() or model.name.lower() == requested_path.name.lower():
                return model.resolve()

    normalized = requested_name.lower()

    exact_matches = [
        model for model in candidates
        if model.name.lower() == normalized
        or model.name.lower() == f"{normalized}.gguf"
        or str(model).lower() == normalized
        or str(model).lower() == f"{normalized}.gguf"
    ]

    if exact_matches:
        return exact_matches[0].resolve()

    partial_matches = [
        model for model in candidates
        if normalized in model.name.lower() or normalized in str(model).lower()
    ]

    if partial_matches:
        return partial_matches[0].resolve()

    print()
    print(f"ERROR: Model not found: {requested_name}")
    print("Available models:")
    for model in candidates:
        print(f"  - {model.name}")
    print()
    sys.exit(1)


def find_model():

    models = get_models()

    if not models:

        print()
        print("ERROR: No GGUF model found.")
        print()
        print(f"Put a .gguf model inside:")
        print(MODELS)
        print()

        sys.exit(1)

    # --------------------------------------------------------
    # Prefer Qwen3 4B if present (lightweight, recommended)
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Otherwise prefer any model containing "qwen"
    # --------------------------------------------------------

    qwen_models = [
        model
        for model in models
        if "qwen" in model.name.lower()
    ]

    if qwen_models:
        return qwen_models[0]

    # --------------------------------------------------------
    # Otherwise use first GGUF
    # --------------------------------------------------------

    return models[0]


# ============================================================
# START LLAMA.CPP
# ============================================================

def start_llama(model):

    gpu_layers = 0

    try:
        gpu_layers = int(
            os.environ.get(
                "PORTABLEAI_GPU_LAYERS",
                "0"
            )
        )
    except ValueError:
        gpu_layers = 0

    command = [
        str(LLAMA),

        "-m",
        str(model),

        # Context size - moderate and safe for local models
        "-c",
        "4096",

        # Do not force all layers onto GPU; many laptops/low-VRAM
        # machines hit CUDA OOM when -ngl is set too high.
        "-ngl",
        str(gpu_layers),

        # Batch size tuned for responsiveness without OOM risk
        "-b",
        "512",

        # Ubatch size - context batch for better quality
        "-ub",
        "256",

        # Number of threads - optimize for multi-core
        "-t",
        "8",

        # Threading type - use thread_pool for better performance
        "-tb",
        "8",

        # Server
        "--host",
        "127.0.0.1",

        "--port",
        str(LLAMA_PORT)
    ]

    print()
    print("=" * 60)
    print("STARTING LLAMA.CPP")
    print("=" * 60)

    print("Model:")
    print(model.name)

    print()
    print("Command:")
    print(" ".join(command))

    print("=" * 60)
    print()

    process = subprocess.Popen(
        command,
        stdout=None,
        stderr=None
    )

    return process


# ============================================================
# WAIT FOR LLAMA SERVER
# ============================================================

def wait_for_llama(timeout=60):

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
    print("WARNING: llama.cpp did not become ready within")
    print(f"{timeout} seconds.")
    print()

    return False


# ============================================================
# HTTP HANDLER
# ============================================================

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            directory=str(WEB),
            **kwargs
        )


    # ========================================================
    # CORS
    # ========================================================

    def end_headers(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        )

        super().end_headers()


    # ========================================================
    # OPTIONS
    # ========================================================

    def do_OPTIONS(self):

        self.send_response(200)
        self.end_headers()


    # ========================================================
    # DELETE
    # ========================================================

    def do_DELETE(self):

        if self.path.startswith("/api/chat/"):

            chat_id = self.path.split("/")[-1]
            chat_file = CHATS / f"{chat_id}.json"

            if chat_file.exists():
                try:
                    chat_file.unlink()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode())
                    return
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
                    return

            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Chat not found"}).encode())
            return

        self.send_response(405)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())


    # ========================================================
    # GET
    # ========================================================

    def do_GET(self):

        # ----------------------------------------------------
        # MODELS
        # ----------------------------------------------------

        if self.path == "/api/models":

            models = [
                model.name
                for model in get_models()
            ]

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps(models).encode()
            )

            return


        # ----------------------------------------------------
        # CONFIG
        # ----------------------------------------------------

        if self.path == "/api/config":

            config_data = {
                "provider":
                server_config.get(
                    "provider",
                    "local"
                ),
                "model":
                server_config.get(
                    "model",
                    ""
                ),
                "base_url":
                server_config.get(
                    "base_url",
                    ""
                )
            }

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps(config_data).encode()
            )

            return


        # ----------------------------------------------------
        # CHAT LIST
        # ----------------------------------------------------

        if self.path == "/api/chats":

            chats = []

            for chat_file in sorted(
                CHATS.glob("*.json"),
                reverse=True
            ):

                try:

                    with open(
                        chat_file,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        chat_data = json.load(f)

                    chats.append({
                        "id": chat_file.stem,
                        "title": chat_data.get(
                            "title",
                            "Untitled"
                        ),
                        "date": chat_data.get(
                            "date",
                            ""
                        )
                    })

                except Exception as e:

                    print(
                        "Could not load chat:",
                        chat_file,
                        e
                    )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps(chats).encode()
            )

            return


        # ----------------------------------------------------
        # LOAD CHAT
        # ----------------------------------------------------

        if self.path.startswith("/api/chat/"):

            chat_id = self.path.split("/")[-1]

            chat_file = CHATS / f"{chat_id}.json"

            if chat_file.exists():

                try:

                    with open(
                        chat_file,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        chat_data = json.load(f)

                    self.send_response(200)

                    self.send_header(
                        "Content-Type",
                        "application/json"
                    )

                    self.end_headers()

                    self.wfile.write(
                        json.dumps(chat_data).encode()
                    )

                except Exception as e:

                    self.send_response(500)

                    self.send_header(
                        "Content-Type",
                        "application/json"
                    )

                    self.end_headers()

                    self.wfile.write(
                        json.dumps({
                            "error": str(e)
                        }).encode()
                    )

            else:

                self.send_response(404)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "error": "Chat not found"
                    }).encode()
                )

            return


        # ----------------------------------------------------
        # HEALTH
        # ----------------------------------------------------

        if self.path == "/health":

            llama_ready = False

            try:

                response = urllib.request.urlopen(
                    f"http://127.0.0.1:{LLAMA_PORT}/health",
                    timeout=2
                )

                llama_ready = response.status == 200

            except Exception:
                llama_ready = False


            self.send_response(
                200 if llama_ready else 503
            )

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "status":
                    "ready"
                    if llama_ready
                    else "loading"
                }).encode()
            )

            return


        # ----------------------------------------------------
        # STATIC FILES
        # ----------------------------------------------------

        super().do_GET()


    # ========================================================
    # POST
    # ========================================================

    def do_POST(self):

        # ----------------------------------------------------
        # CONFIG
        # ----------------------------------------------------

        if self.path == "/api/config":

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            try:

                data = json.loads(
                    body.decode("utf-8")
                )

                provider = str(
                    data.get(
                        "provider",
                        server_config.get("provider", "local")
                    )
                ).strip().lower() or "local"

                selected_model = data.get(
                    "model",
                    server_config.get("model", "")
                )

                server_config["provider"] = provider

                if provider == "local":
                    available_models = [
                        model.name
                        for model in get_models()
                    ]

                    if (
                        selected_model
                        and selected_model not in available_models
                    ):

                        self.send_response(400)

                        self.send_header(
                            "Content-Type",
                            "application/json"
                        )

                        self.end_headers()

                        self.wfile.write(
                            json.dumps({
                                "error":
                                "Selected model does not exist."
                            }).encode()
                        )

                        return

                    resolved_model = resolve_model_name(selected_model)
                    server_config["model"] = str(resolved_model)

                else:
                    server_config["model"] = str(selected_model or "gpt-4o-mini")
                    server_config["base_url"] = str(
                        data.get(
                            "base_url",
                            server_config.get("base_url", "")
                        )
                    ).strip()
                    server_config["api_key"] = str(
                        data.get(
                            "api_key",
                            server_config.get("api_key", "")
                        )
                    )

                try:
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(server_config, f, indent=2)
                except Exception:
                    pass

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "success": True,
                        "provider": provider,
                        "model": server_config.get("model", selected_model)
                    }).encode()
                )

            except Exception as e:

                self.send_response(400)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "error": str(e)
                    }).encode()
                )

            return


        # ----------------------------------------------------
        # SAVE CHAT
        # ----------------------------------------------------

        if self.path == "/api/save-chat":

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            try:

                chat_data = json.loads(
                    body.decode("utf-8")
                )

                chat_id = chat_data.get(
                    "id",
                    datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )
                )

                chat_file = (
                    CHATS /
                    f"{chat_id}.json"
                )

                with open(
                    chat_file,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        chat_data,
                        f,
                        indent=2,
                        ensure_ascii=False
                    )

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "success": True,
                        "id": chat_id
                    }).encode()
                )

            except Exception as e:

                self.send_response(400)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "error": str(e)
                    }).encode()
                )

            return


        # ----------------------------------------------------
        # CHAT COMPLETIONS
        # ----------------------------------------------------

        if self.path == "/v1/chat/completions":

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            self._proxy_to_llama(body)

            return


        super().do_POST()


    # ========================================================
    # PROXY TO LLAMA
    # ========================================================

    def _proxy_to_llama(self, body):

        try:

            request_data = json.loads(
                body.decode("utf-8")
            )

            incoming_messages = request_data.get(
                "messages",
                []
            )

            conversation = [
                message
                for message in incoming_messages
                if message.get("role") != "system"
            ]

            request_data["messages"] = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                }
            ] + conversation

            provider = str(
                server_config.get("provider", "local")
            ).strip().lower() or "local"

            if provider == "local":
                active_model = server_config.get(
                    "model",
                    ""
                )

                if active_model:
                    request_data["model"] = str(
                        resolve_model_name(active_model)
                    )
                else:
                    request_data["model"] = str(
                        resolve_model_name()
                    )

                request_data["temperature"] = 0.1
                request_data["max_tokens"] = 256
                request_data["top_p"] = 0.9
                request_data["frequency_penalty"] = 0.1
                request_data["presence_penalty"] = 0.0
                request_data["repeat_penalty"] = 1.1
                request_data["stop"] = [
                    "<|im_end|>",
                    "<|end_of_text|>",
                    "\n\nUser:",
                    "\n\nHuman:"
                ]
                request_data["stream"] = True
                modified_body = json.dumps(
                    request_data
                ).encode("utf-8")

                print()
                print("=" * 60)
                print("PORTABLEAI REQUEST")
                print("=" * 60)
                print("Active model:", server_config.get("model", "unknown"))
                print("Messages:", len(request_data["messages"]))
                print("Temperature:", request_data["temperature"])
                print("Max tokens:", request_data["max_tokens"])
                print("=" * 60)

                url = f"http://127.0.0.1:{LLAMA_PORT}/v1/chat/completions"
                headers = {"Content-Type": "application/json"}
                req = urllib.request.Request(url, data=modified_body, headers=headers)

                with urllib.request.urlopen(req, timeout=600) as response:
                    self.send_response(response.status)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()

                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()

                return

            # ------------------------------
            # Remote OpenAI-compatible provider
            # ------------------------------
            target_model = str(request_data.get("model") or server_config.get("model") or "gpt-4o-mini")
            request_data["model"] = target_model
            request_data["messages"] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + conversation
            request_data["stream"] = True

            base_url = normalize_base_url(
                provider,
                str(server_config.get("base_url") or default_base_url_for_provider(provider))
            )

            api_key = str(server_config.get("api_key", "")).strip()
            url = f"{base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}

            if api_key:
                if provider == "gemini":
                    headers["x-goog-api-key"] = api_key
                    headers["Authorization"] = f"Bearer {api_key}"
                else:
                    headers["Authorization"] = f"Bearer {api_key}"

            if provider == "openrouter":
                headers["HTTP-Referer"] = "http://127.0.0.1:9000"
                headers["X-Title"] = "PortableAI"

            if provider == "gemini":
                headers["Accept"] = "application/json"

            modified_body = json.dumps(request_data).encode("utf-8")
            req = urllib.request.Request(url, data=modified_body, headers=headers)

            with urllib.request.urlopen(req, timeout=300) as response:
                self.send_response(response.status)
                content_type = response.headers.get_content_type()
                self.send_header("Content-Type", content_type if content_type else "application/json")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()

            return


        except urllib.error.HTTPError as e:

            error_body = e.read().decode(
                "utf-8",
                errors="replace"
            )

            print()
            print("llama.cpp HTTP ERROR:")
            print(error_body)

            try:

                self.send_response(
                    e.code
                )

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    error_body.encode()
                )

            except Exception:
                pass


        except urllib.error.URLError as e:

            print()
            print(
                "ERROR connecting to llama.cpp:",
                e
            )

            try:

                self.send_response(503)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "error":
                        f"Cannot connect to llama server: {e}"
                    }).encode()
                )

            except Exception:
                pass


        except Exception as e:

            print()
            print(
                "Proxy error:",
                repr(e)
            )

            try:

                self.send_response(500)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "error": str(e)
                    }).encode()
                )

            except Exception:
                pass


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("PORTABLE LOCAL AI")
    print("=" * 60)
    print()

    provider = "local"
    requested_model = ""
    api_key = ""
    base_url = ""

    # Smart argument parsing:
    # If only 1 arg: it's either model name or auto-select if it's "local"
    # If 2+ args: first is model name, second is provider
    if len(sys.argv) > 1:
        arg1 = sys.argv[1].strip() if sys.argv[1] else ""
        
        # If arg1 is a known provider AND we have exactly 2 args, treat as provider only
        if arg1 in {"local", "openai", "openrouter", "deepseek", "gemini", "custom"} and len(sys.argv) == 2:
            provider = arg1
            requested_model = ""  # Auto-select
        else:
            requested_model = arg1  # Treat as model name
    
    if len(sys.argv) > 2:
        provider = sys.argv[2].strip().lower() or "local"
    
    if len(sys.argv) > 3:
        api_key = sys.argv[3]
    if len(sys.argv) > 4:
        base_url = sys.argv[4]

    if provider not in {"local", "openai", "openrouter", "deepseek", "gemini", "custom"}:
        provider = "local"

    server_config["provider"] = provider
    server_config["api_key"] = api_key
    server_config["base_url"] = normalize_base_url(provider, base_url)

    if provider == "local":
        if not LLAMA.exists():
            print("ERROR: llama-server not found:")
            print(LLAMA)
            sys.exit(1)

        model = resolve_model_name(requested_model)
        server_config["model"] = str(model.resolve())
        print("Model selected:")
        print(model.name)
    else:
        model_name = requested_model or server_config.get("model") or "gpt-4o-mini"
        server_config["model"] = model_name
        print("Provider selected:")
        print(provider)
        print("Model:")
        print(model_name)
        print("Base URL:")
        print(normalize_base_url(provider, base_url or default_base_url_for_provider(provider)))

    # Save config so the UI and future restarts persist the selection.
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(server_config, f, indent=2)
    except Exception as e:
        print(f"Config save warning: {e}")

    if provider == "local":
        # --------------------------------------------------------
        # Check llama executable
        # --------------------------------------------------------
        pass

    print()

    model = None

    if provider == "local":
        model = resolve_model_name(requested_model)
        server_config["model"] = str(model.resolve())

        # --------------------------------------------------------
        # Show all available models
        # --------------------------------------------------------

        models = get_models()

        print("Available GGUF models:")

        for available_model in models:

            marker = (
                " <-- ACTIVE"
                if available_model == model
                else ""
            )

            print(
                f"  - {available_model.name}{marker}"
            )

        print()


        # --------------------------------------------------------
        # Start llama
        # --------------------------------------------------------

        llama_process = start_llama(model)


        # --------------------------------------------------------
        # Wait for llama
        # --------------------------------------------------------

        wait_for_llama(60)

    else:
        print("Provider mode enabled. Local llama.cpp server is not started.")
        llama_process = None


    if provider == "local":
        model_label = model.name if model else "local"
    else:
        model_label = server_config.get("model", requested_model or "gpt-4o-mini")


    # --------------------------------------------------------
    # Start web/API server
    # --------------------------------------------------------

    server = ThreadingHTTPServer(
        ("127.0.0.1", PORT),
        MyHTTPRequestHandler
    )


    print("=" * 60)
    print("PORTABLE AI READY")
    print("=" * 60)

    print(
        f"Web/API: http://127.0.0.1:{PORT}"
    )

    print(
        f"llama.cpp: http://127.0.0.1:{LLAMA_PORT}"
    )

    print(
        f"Active model: {model_label}"
    )

    print("=" * 60)
    print()


    webbrowser.open(
        f"http://127.0.0.1:{PORT}"
    )


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print()
        print("Shutting down PortableAI...")


        if llama_process is not None:
            llama_process.terminate()

            try:

                llama_process.wait(
                    timeout=10
                )

            except subprocess.TimeoutExpired:

                llama_process.kill()


        server.shutdown()

        sys.exit(0)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()