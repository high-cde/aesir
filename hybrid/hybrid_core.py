#!/usr/bin/env python3
import os, json, socket, subprocess, sys, logging
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "/root/zdos-aesir/aesir")
sys.path.insert(0, os.environ.get("AESIR_HOME") or str(Path(__file__).resolve().parent.parent))  # zdos-dsn-code-align v1: non solo /root
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
