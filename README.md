# Æsir — ZDOS Orchestration Layer

Æsir contains components for evaluating transaction intents through a Rust policy engine and a Python orchestration layer. The repository also includes a DSN balance gate, a Tor configuration, and scripts for starting or managing parts of the system.

## Components

| Path | Purpose |
| --- | --- |
| `policy/` | Rust command-line policy engine. It reads one intent as JSON from standard input and writes a JSON decision to standard output. |
| `dsn_gate.py` and `dsn.env` | Python helpers that query a token balance through Polygon JSON-RPC and apply configured DSN thresholds. |
| `hybrid/hybrid_core.py` | Python Unix-socket service that applies the DSN check to non-human requesters, calls the policy engine, and forwards approved intents to a signing socket. |
| `nexus/torrc` | Tor configuration with SOCKS and control ports and a data directory. |
| `status_server.py` | HTTP status handler bound to `127.0.0.1:8080`; it serves status data at `/status`. |
| `scripts/start-aesir.sh` | Shell launcher for Tor and the hybrid process. Its path assumptions are described under [Runtime notes](#runtime-notes). |
| `aesir-advance.sh` | Administrative script that writes service/configuration files and operates on systemd. Review it before use. |

## Policy engine

The policy engine deserializes an intent with these fields: `asset`, `amount_atomic`, `destination`, `network_constraints`, `requester`, and the optional `hourly_limit_override`. The source applies a default amount limit of `500000000` atomic units when no override is provided. An intent is approved only when its amount is within the selected limit and at least one network constraint contains `tor` or `onion`; otherwise it is denied.

Build the policy component from the repository root with Cargo:

```sh
cargo build --release --manifest-path policy/Cargo.toml
```

To send a sample intent directly to the built policy executable:

```sh
printf '%s\n' '{"asset":"ZEPH","amount_atomic":1000000,"destination":"0x0000000000000000000000000000000000000000","network_constraints":["tor"],"requester":"kira"}' \
  | ./policy/target/release/policy_engine
```

This exercises the policy executable only; it does not start the Python service, query DSN, or connect to a signer. The executable prints a JSON decision containing `approved`, `reason`, `token_hash`, and `expires_unix`.

## DSN configuration

`dsn_gate.py` reads these settings from its configured environment file when present, with defaults in the Python code:

- `DSN_CONTRACT`: token contract address.
- `POLYGON_RPC`: preferred Polygon JSON-RPC endpoint; the code also defines fallback endpoints.
- `DSN_MIN_BALANCE_WEI` and `DSN_HIGH_LIMIT_WEI`: DSN balance thresholds.
- `DSN_HOURLY_BASE` and `DSN_HOURLY_BOOSTED`: policy limit values selected by the DSN gate.

The checked-in `dsn.env` contains concrete values. The gate uses the ERC-20 `balanceOf` call and returns zero if the address is malformed or all RPC attempts fail. A successful RPC response is treated as the balance result; verify the endpoint and contract values before relying on it.

## Runtime notes

The checked-in runtime scripts are not currently a self-contained installation procedure. The repository has `hybrid/`, `nexus/`, and `policy/` at its root, while `scripts/start-aesir.sh` refers to `aesir/nexus/torrc`. The Python runtime also uses fixed paths under `/root/zdos-aesir/aesir` for imports, configuration, logs, sockets, and the policy executable. As a result, the scripts' paths must be reconciled with the intended deployment layout before attempting to start the full service.

The Python DSN gate imports `requests`, but the repository does not include a Python dependency manifest. The policy build command above covers only the Rust component. No end-to-end test command or test suite is included in the source files reviewed.
