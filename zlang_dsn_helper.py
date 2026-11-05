#!/usr/bin/env python3
"""Helper callable from ZLang or scripts"""
import sys, json, socket
from pathlib import Path
sys.path.insert(0, "/root/zdos-aesir/aesir")
import os
sys.path.insert(0, os.environ.get("AESIR_HOME") or str(Path(__file__).resolve().parent))  # zdos-dsn-code-align v1: non solo /root
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
