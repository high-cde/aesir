#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, subprocess
from pathlib import Path
import sys
sys.path.insert(0, "/root/zdos-aesir/aesir")
import os
sys.path.insert(0, os.environ.get("AESIR_HOME") or str(Path(__file__).resolve().parent))  # zdos-dsn-code-align v1: non solo /root
from dsn_gate import get_balance

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            try:
                log_tail = Path("/var/log/aesir/hybrid.log").read_text().splitlines()[-5:]
            except:
                log_tail = []
            data = {
                "hybrid": "running" if subprocess.run(["pgrep","-f","hybrid_core"], capture_output=True).returncode == 0 else "stopped",
                "last_logs": log_tail,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
