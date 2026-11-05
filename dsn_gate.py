#!/usr/bin/env python3
# ZDOS:DSN-CODE-ALIGN v1 — managed by zdos-dsn-code-align.sh (aesir plugin).
# $DSN / NETkali: ERC-20 on Polygon PoS (chain id 137), 18 decimals.
# Contract 0xfc90516a1f736FaC557e09D8853dB80dA192c296 · portal https://x-zdos.it/dsn
# Access layer only: read-only balanceOf, no keys, no transactions.
import os, requests, time
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _readable(p: Path) -> bool:
    try:
        return p.is_file() and os.access(p, os.R_OK)
    except OSError:  # e.g. /root not traversable for non-root users
        return False

_LEGACY_ENV = Path("/root/zdos-aesir/aesir/dsn.env")
ENV_PATH = Path(os.getenv("DSN_ENV", str(_HERE / "dsn.env")))
if not _readable(ENV_PATH) and _readable(_LEGACY_ENV):
    ENV_PATH = _LEGACY_ENV
if _readable(ENV_PATH):
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DSN = os.getenv("DSN_CONTRACT", "0xfc90516a1f736FaC557e09D8853dB80dA192c296")
CHAIN_ID = int(os.getenv("DSN_CHAIN_ID", "137"))
# rpc.ankr.com/polygon and polygon-rpc.com now require an API key and answer
# with a JSON-RPC error (ankr even with HTTP 200): never use them as defaults.
_RPC_CANDIDATES = [
    os.getenv("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com"),
    os.getenv("POLYGON_RPC_FALLBACK", "https://polygon.drpc.org"),
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon.drpc.org",
]
RPCS = list(dict.fromkeys(u for u in _RPC_CANDIDATES if u))
MIN_WEI = int(os.getenv("DSN_MIN_BALANCE_WEI", "1000000000000000000"))
HIGH_WEI = int(os.getenv("DSN_HIGH_LIMIT_WEI", "10000000000000000000"))
_CHAIN_OK = {}


class RPCError(Exception):
    pass


def _call(rpc, method, params):
    r = requests.post(rpc, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=6)
    r.raise_for_status()
    body = r.json()
    # A JSON-RPC error must NOT be read as "balance 0": try the next endpoint.
    if not isinstance(body, dict) or "error" in body or "result" not in body:
        raise RPCError(f"{rpc}: {body.get('error') if isinstance(body, dict) else body}")
    return body["result"]


def _chain_ok(rpc) -> bool:
    if rpc not in _CHAIN_OK:
        try:
            _CHAIN_OK[rpc] = int(_call(rpc, "eth_chainId", []), 16) == CHAIN_ID
        except Exception:
            return False
    return _CHAIN_OK[rpc]


def get_balance(address: str) -> int:
    """balanceOf(address) in wei; 0 if the address is malformed or every RPC fails (fail-closed)."""
    if not isinstance(address, str) or not address.startswith("0x") or len(address) != 42:
        return 0
    try:
        int(address[2:], 16)
    except ValueError:
        return 0
    data = "0x70a08231" + address[2:].lower().zfill(64)
    for rpc in RPCS:
        if not _chain_ok(rpc):
            continue
        try:
            return int(_call(rpc, "eth_call", [{"to": DSN, "data": data}, "latest"]), 16)
        except Exception:
            continue
    return 0


def has_min_dsn(address: str, min_wei=None) -> bool:
    return get_balance(address) >= (MIN_WEI if min_wei is None else min_wei)


def get_limit_for(address: str) -> int:
    bal = get_balance(address)
    if bal >= HIGH_WEI:
        return int(os.getenv("DSN_HOURLY_BOOSTED", "5000000000"))
    if bal >= MIN_WEI:
        return int(os.getenv("DSN_HOURLY_BASE", "500000000"))
    return 0
