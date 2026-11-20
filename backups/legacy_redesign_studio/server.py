import os
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from decompose import decompose_poster

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))


class StudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STUDIO_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/decompose":
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            raw_name = urllib.parse.unquote(self.headers.get("X-Filename", "upload.png"))
            safe_name = os.path.basename(raw_name) or "upload.png"
            upload_path = os.path.join(STUDIO_DIR, "_uploaded_" + safe_name)
            with open(upload_path, "wb") as f:
                f.write(data)
            for old in os.listdir(os.path.join(STUDIO_DIR, "layers")):
                if old.endswith(".png"):
                    os.remove(os.path.join(STUDIO_DIR, "layers", old))
            decompose_poster(upload_path, STUDIO_DIR)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    os.chdir(STUDIO_DIR)
    server = HTTPServer(("127.0.0.1", 8765), StudioHandler)
    print("Redesign Studio running at http://127.0.0.1:8765")
    server.serve_forever()
