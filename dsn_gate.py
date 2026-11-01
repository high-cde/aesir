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
