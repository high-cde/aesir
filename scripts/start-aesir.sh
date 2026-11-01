#!/bin/bash
set -e
sudo mkdir -p /var/run/zdos /var/lib/zdos-tor
sudo chown -R $USER:$USER /var/run/zdos || true
if ! pgrep -x tor >/dev/null; then
  sudo tor -f aesir/nexus/torrc &
  sleep 2
fi
python3 aesir/hybrid/hybrid_core.py &
echo "Æsir + DSN running"
echo "Test: echo '{\"asset\":\"ZEPH\",\"amount_atomic\":1000000,\"destination\":\"0xTUO_WALLET\",\"network_constraints\":[\"tor\"],\"requester\":\"kira\"}' | socat - UNIX-CONNECT:/var/run/zdos/kira_intent.sock"
