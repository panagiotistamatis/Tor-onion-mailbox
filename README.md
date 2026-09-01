# Tor v3 Onion Service — Private Onion Mailbox API

A Tor v3 Onion (Hidden) Service that runs a small, **client-authorized** message
API. Two authorized users (`alice`, `bob`) send each other messages over Tor, and
neither of them, nor the server, ever exposes an IP address.

**Why I built it.** I wanted to put together a full service that stays private
from the ground up: anonymous hosting (onion v3), cryptographic access control
(x25519 client authorization), encrypted transport. Then I wanted to actually
check that those properties held instead of just assuming they did.

**Status.** Working proof of concept, done for my Computer Systems Security
course. I captured traffic with Wireshark and confirmed the transport is
encrypted and there's no IP or DNS leak.

```
Tor :80  ->  nginx 127.0.0.1:8080  ->  uvicorn/FastAPI 127.0.0.1:8000
```

## Highlights

- **Anonymous hosting.** The service only exists as a `.onion`. The server's real IP is never published.
- **Access control at the network layer.** You need an authorized x25519 key to even reach the service (Tor v3 client authorization), so the check happens before HTTP.
- **Private by design.** Everything binds to localhost, logging is off, and messages live only in memory (nothing on disk).
- **Verified, not assumed.** The Wireshark capture shows only encrypted traffic: no plaintext HTTP, no real IP, no DNS queries.

## Quick start

```bash
# Bare metal (Debian / Ubuntu / Kali)
sudo scripts/setup.sh      # installs tor + nginx, deploys configs, creates the onion service
scripts/run_app.sh         # runs the FastAPI backend on 127.0.0.1:8000

# …or the local Docker stack (api + nginx + tor)
docker compose -f docker/docker-compose.yml up --build

# Try the client demo (against a locally running API)
python examples/mailbox_demo.py
```

## Documentation

- **[Detailed overview](docs/detailed-overview.md)** — the full write-up: architecture diagram, deployment screenshots, performance measurements, references.
- **[Architecture](docs/architecture.md)** — components, port chain, request/response flow.
- **[Threat model](docs/threat-model.md)** — what the design protects and where it falls short.

## Tech stack

Tor (onion v3 · x25519 client authorization) · nginx · FastAPI / uvicorn ·
Docker · Wireshark (verification) · Debian / Kali Linux.

## Author

**Panagiotis Stamatis** — [@panagiotistamatis](https://github.com/panagiotistamatis)

## License

[MIT](LICENSE)
