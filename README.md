# Æsir — ZDOS Orchestration Layer + Crypto Dashboard

Æsir contiene il policy engine Rust, il gate $DSN (Polygon + Solana) e ora una **dashboard crypto reale** client-side.

## Dashboard

Apri `dashboard.html` (o abilita GitHub Pages) per:
- Visualizzare balance $DSN su Polygon e Solana
- Connettere MetaMask / Phantom
- Controllare status del gate e RPC
- Query manuali

**GitHub Pages:** Settings → Pages → Deploy from branch `main` / root. Il sito sarà su `https://high-cde.github.io/aesir/`.

## Componenti backend

| Path | Purpose |
| --- | --- |
| `policy/` | Rust policy engine (JSON intent → decisione) |
| `dsn_gate.py` + `dsn.env` | Gate balance $DSN via Polygon RPC |
| `hybrid/hybrid_core.py` | Servizio Unix-socket che applica gate + policy |
| `status_server.py` | HTTP status su 127.0.0.1:8080 |
| `dashboard.html` | Dashboard crypto frontend |

## Policy engine

```sh
cargo build --release --manifest-path policy/Cargo.toml
```

## Runtime

I path in alcuni script sono hardcoded (`/root/zdos-aesir/...`). Usa variabili d'ambiente o adatta i path prima del deploy completo.

$DSN Contract Polygon: `0xfc90516a1f736FaC557e09D8853dB80dA192c296`
