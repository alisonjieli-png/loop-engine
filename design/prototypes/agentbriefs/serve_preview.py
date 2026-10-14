"""Serve three prototype files on loopback only. No API, uploads or directory listing."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
FILES = {"/": ("index.html", "text/html; charset=utf-8"),
         "/index.html": ("index.html", "text/html; charset=utf-8"),
         "/styles.css": ("styles.css", "text/css; charset=utf-8"),
         "/app.js": ("app.js", "text/javascript; charset=utf-8")}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'"


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def do_POST(self):
        self.send_error(405, "This local prototype accepts no submissions")

    def respond(self, head):
        item = FILES.get(urlsplit(self.path).path)
        if item is None:
            self.send_error(404, "No prototype resource at this address")
            return
        path = ROOT / item[0]
        if path.is_symlink():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        for key, value in {"Content-Type": item[1], "Content-Length": str(len(body)),
                           "Content-Security-Policy": CSP, "Cache-Control": "no-store",
                           "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                           "X-Frame-Options": "DENY"}.items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Preview)
    print("http://127.0.0.1:" + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
