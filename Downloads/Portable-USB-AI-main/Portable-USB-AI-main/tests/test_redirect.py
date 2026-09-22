import threading
import time
import http.client

import importlib.util, os

# Load app/server.py by file path (not as a package)
server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'server.py'))
spec = importlib.util.spec_from_file_location('server', server_path)
server_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_mod)

ThreadingHTTPServer = server_mod.ThreadingHTTPServer
MyHTTPRequestHandler = server_mod.MyHTTPRequestHandler
PORT = server_mod.PORT
LLAMA_PORT = server_mod.LLAMA_PORT


def run_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), MyHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == '__main__':
    server = run_server()
    time.sleep(0.5)

    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    conn.request("GET", "/")
    res = conn.getresponse()
    print(res.status)
    print(res.getheader('Location'))

    server.shutdown()
    server.server_close()
