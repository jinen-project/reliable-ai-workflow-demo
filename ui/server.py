from __future__ import annotations
import html, json, sys, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from scenarios.run_scenarios import run_all


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        out = run_all()
        body = "<h1>Reliable AI Workflow Demo</h1><p>Local synthetic scenarios</p><pre>" + html.escape(json.dumps(out, indent=2)) + "</pre><p>Try CLI: make verify</p>"
        raw = ("<html><body style='font-family:system-ui;max-width:1100px;margin:40px'>" + body + "</body></html>").encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def log_message(self, *_): pass


if __name__ == "__main__":
    print("http://127.0.0.1:8765")
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()

