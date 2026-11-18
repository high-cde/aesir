# Æsir — ZDOS Orchestration Layer + Crypto Dashboard

> **STATUS: MAINNET ONLINE** ⚡⚖️
> Branch `main` allineato, pulito e sincronizzato.
> Ultimo allineamento: 2026-11-18

Æsir contiene il policy engine Rust, il gate $DSN (Polygon + Solana) e una **dashboard crypto reale** client-side che replica lo stile estetico di [x-zdos.it](https://x-zdos.it) (dark + JetBrains Mono + emerald #00ff88 + Tailwind).

## Dashboard

- `index.html` / `dashboard.html`: dashboard funzionale con:
  - Balance $DSN su Polygon e Solana via RPC pubblici
  - Connessione Phantom / MetaMask
  - Status gate Æsir e test RPC
  - Query manuali

**Per metterla online (GitHub Pages):**
1. Vai su **Settings → Pages**
2. Source: Deploy from a branch → `main` → `/ (root)`
3. Sito: `https://high-cde.github.io/aesir/`

APIs pubbliche attive (polygon.drpc.org, Solana mainnet). Nessuna chiave richiesta per uso base.

## Componenti backend

| Path | Purpose |
| --- | --- |
| `policy/` | Rust policy engine (JSON intent → decisione) |
| `dsn_gate.py` + `dsn.env` | Gate balance $DSN via Polygon RPC |
| `hybrid/hybrid_core.py` | Servizio Unix-socket che applica gate + policy |
| `status_server.py` | HTTP status su 127.0.0.1:8080 |
| `index.html` / `dashboard.html` | Dashboard crypto frontend |

## Policy engine

```sh
cargo build --release --manifest-path policy/Cargo.toml
```

## Runtime

I path in alcuni script sono hardcoded (`/root/zdos-aesir/...`). Usa variabili d'ambiente o adatta i path prima del deploy completo.

$DSN Contract Polygon: `0xfc90516a1f736FaC557e09D8853dB80dA192c296`

## Mainnet
- Default branch: `main`
- Stato: **LIVE / MAINNET**
- Sincronizzazione: Completa
