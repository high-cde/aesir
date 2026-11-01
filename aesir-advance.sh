#!/bin/bash
# ÆSIR STRATEGIC ADVANCEMENT — Full sequence
# 1. Multi-RPC  2. systemd  3. Logging  4. Status endpoint  5. ZLang helper
set -euo pipefail

AESIR="/root/zdos-aesir/aesir"
cd "$AESIR"

echo "=== 1/5 Multi-RPC Fallback ==="
cat > dsn_gate.py << 'EOF'
#!/usr/bin/env python3
import os, requests, time
from pathlib import Path

ENV_PATH = Path("/root/zdos-aesir/aesir/dsn.env")
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

DSN = os.getenv("DSN_CONTRACT", "0xfc90516a1f736FaC557e09D8853dB80dA192c296")
RPCS = [
    os.getenv("POLYGON_RPC", "https://rpc.ankr.com/polygon"),
    "https://polygon.llamarpc.com",
    "https://1rpc.io/matic",
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-rpc.com",
]
MIN_WEI = int(os.getenv("DSN_MIN_BALANCE_WEI", "1000000000000000000"))
HIGH_WEI = int(os.getenv("DSN_HIGH_LIMIT_WEI", "10000000000000000000"))

def _call(rpc, method, params):
    r = requests.post(rpc, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=6)
    r.raise_for_status()
    return r.json()

def get_balance(address: str) -> int:
    if not address.startswith("0x") or len(address) != 42:
        return 0
    data = "0x70a08231" + address[2:].lower().zfill(64)
    for rpc in RPCS:
        try:
            result = _call(rpc, "eth_call", [{"to": DSN, "data": data}, "latest"])
            return int(result.get("result", "0x0"), 16)
        except Exception:
            continue
    return 0

def has_min_dsn(address: str, min_wei=None) -> bool:
    return get_balance(address) >= (min_wei or MIN_WEI)

def get_limit_for(address: str) -> int:
    bal = get_balance(address)
    if bal >= HIGH_WEI:
        return int(os.getenv("DSN_HOURLY_BOOSTED", "5000000000"))
    if bal >= MIN_WEI:
        return int(os.getenv("DSN_HOURLY_BASE", "500000000"))
    return 0
EOF
chmod +x dsn_gate.py

echo "=== 2/5 Systemd Service ==="
cat > /etc/systemd/system/aesir-hybrid.service << 'EOF'
[Unit]
Description=Æsir Hybrid Core (DSN-aware)
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/zdos-aesir
ExecStart=/usr/bin/python3 /root/zdos-aesir/aesir/hybrid/hybrid_core.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable aesir-hybrid.service
systemctl restart aesir-hybrid.service || true

echo "=== 3/5 Structured Logging ==="
mkdir -p /var/log/aesir
cat > hybrid/hybrid_core.py << 'EOF'
#!/usr/bin/env python3
import os, json, socket, subprocess, sys, logging
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "/root/zdos-aesir/aesir")
from dsn_gate import has_min_dsn, get_limit_for, get_balance

logging.basicConfig(
    filename="/var/log/aesir/hybrid.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("aesir")

SOCK_DIR = Path("/var/run/zdos")
KIRA_SOCK = SOCK_DIR / "kira_intent.sock"
SIGN_SOCK = SOCK_DIR / "sign.sock"
POLICY_BIN = Path("/root/zdos-aesir/aesir/policy/target/release/policy_engine")

def ensure_sockets():
    SOCK_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SOCK_DIR, 0o770)
    for s in [KIRA_SOCK, SIGN_SOCK]:
        if s.exists(): s.unlink()

def listen_intent():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(KIRA_SOCK))
    os.chmod(KIRA_SOCK, 0o660)
    sock.listen(1)
    log.info("Hybrid listening (DSN + logging)")
    print("[hybrid] Listening (DSN + logging)")
    while True:
        conn, _ = sock.accept()
        data = conn.recv(8192)
        try:
            intent = json.loads(data.decode())
            wallet = intent.get("destination") or intent.get("requester_wallet", "")
            bal = get_balance(wallet) if wallet else 0
            log.info(f"Intent from {wallet} balance={bal} amount={intent.get('amount_atomic')}")
            if intent.get("requester") != "human":
                if not has_min_dsn(wallet):
                    resp = {"approved": False, "reason": "Insufficient DSN"}
                    conn.send(json.dumps(resp).encode())
                    log.info(f"DENIED {wallet}")
                    conn.close()
                    continue
                intent["hourly_limit_override"] = get_limit_for(wallet)
            result = call_policy_engine(intent)
            if result.get("approved"):
                forward_to_sign(result, intent)
                log.info(f"APPROVED {wallet}")
            else:
                log.info(f"POLICY_DENIED {wallet} {result.get('reason')}")
            conn.send(json.dumps(result).encode())
        except Exception as e:
            log.error(f"Error: {e}")
            conn.send(json.dumps({"approved": False, "reason": str(e)}).encode())
        conn.close()

def call_policy_engine(intent):
    if POLICY_BIN.exists():
        proc = subprocess.run([str(POLICY_BIN)], input=json.dumps(intent).encode(), capture_output=True, timeout=5)
        if proc.returncode == 0:
            return json.loads(proc.stdout.decode())
    return {"approved": False, "reason": "policy_engine unavailable"}

def forward_to_sign(approval, intent):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(SIGN_SOCK))
            s.send(json.dumps({"approval": approval, "intent": intent}).encode())
    except Exception as e:
        log.warning(f"sign forward failed: {e}")

if __name__ == "__main__":
    ensure_sockets()
    listen_intent()
EOF
chmod +x hybrid/hybrid_core.py

echo "=== 4/5 Status Endpoint ==="
cat > status_server.py << 'EOF'
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, subprocess
from pathlib import Path
import sys
sys.path.insert(0, "/root/zdos-aesir/aesir")
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
EOF
chmod +x status_server.py

cat > /etc/systemd/system/aesir-status.service << 'EOF'
[Unit]
Description=Æsir Status Endpoint
After=aesir-hybrid.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/zdos-aesir/aesir/status_server.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable aesir-status.service
systemctl restart aesir-status.service || true

echo "=== 5/5 ZLang Helper ==="
mkdir -p /root/zdos-aesir/Zlang/examples
cat > /root/zdos-aesir/Zlang/examples/dsn_check.zl << 'EOF'
; ZLang helper example – call external DSN gate
; (compile later with ZLang toolchain when ready)
; emit "Checking DSN balance via hybrid socket..."
; halt
EOF

cat > /root/zdos-aesir/aesir/zlang_dsn_helper.py << 'EOF'
#!/usr/bin/env python3
"""Helper callable from ZLang or scripts"""
import sys, json, socket
from pathlib import Path
sys.path.insert(0, "/root/zdos-aesir/aesir")
from dsn_gate import get_balance, has_min_dsn

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: zlang_dsn_helper.py <wallet>")
        sys.exit(1)
    addr = sys.argv[1]
    print(json.dumps({
        "wallet": addr,
        "balance": get_balance(addr),
        "has_min": has_min_dsn(addr)
    }))
EOF
chmod +x /root/zdos-aesir/aesir/zlang_dsn_helper.py

echo ""
echo "=== SEQUENZA COMPLETA ==="
echo "1. Multi-RPC attivo"
echo "2. systemd: systemctl status aesir-hybrid"
echo "3. Log: tail -f /var/log/aesir/hybrid.log"
echo "4. Status: curl http://127.0.0.1:8080/status"
echo "5. ZLang helper: python3 /root/zdos-aesir/aesir/zlang_dsn_helper.py 0xe5b8ae2eebe07808f129530926562e39baf0b063"
echo ""
echo "Riavvia hybrid se necessario:"
echo "systemctl restart aesir-hybrid"
