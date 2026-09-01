# Architecture

This is the longer look at the four-layer design of the Onion Mailbox service:
what each component does, the exact port chain, the request/response sequences
for the main endpoints, and why I made the design choices I did.

## Overview

```
                Tor SOCKS :9050                 onion :80
  Client  ─────────────────────────►  Tor  ──────────────►  Onion Service
 (alice / bob)   3-hop circuit       network                     │
                                                                 ▼
                                                    nginx  127.0.0.1:8080
                                                                 │  proxy_pass
                                                                 ▼
                                                 uvicorn/FastAPI 127.0.0.1:8000
```

Every server-side component binds to loopback only. The one endpoint reachable
from outside is the Tor onion service. There's no public TCP port on the host,
and without a valid client-authorization key you can't even contact the onion
service.

## Components and responsibilities

### 1. Tor network
This is the anonymizing transport. A client connects through a 3-hop circuit, so
no single relay knows both the client and the destination. The onion service
reaches the client back through the rendezvous protocol, so the server never
learns the client's IP and the client never learns the server's.

### 2. Onion Service v3 (Tor `:80`)
- The server's identity is an **Ed25519** keypair. The public key, a checksum,
  and a version byte get Base32-encoded into the 56-character `.onion` address:
  `Base32(pubkey || checksum || version)` (see "How the onion address is derived"
  below). Its strength is comparable to ~RSA-3072.
- `torrc` maps the onion virtual port `80` to the local nginx socket:
  `HiddenServicePort 80 127.0.0.1:8080`.
- **Client authorization** is enforced here (there's a section on it below). This
  is the access-control boundary for the whole system. It sits below the
  application, so unauthorized parties never reach HTTP at all.

### 3. nginx reverse proxy (`127.0.0.1:8080`)
- Binds to loopback only, so it's unreachable except through the onion service.
- `access_log off`, so no per-request client trail gets written to disk (minimal
  logging / data minimization).
- Relaxed proxy timeouts (connect 5s, read/send 20s) so Tor's higher and more
  variable round-trip latency doesn't trip anything up.
- Forwards to the FastAPI app with `proxy_pass http://127.0.0.1:8000`.

### 4. FastAPI application (`127.0.0.1:8000`)
- Implements the mailbox REST API (see `../app/app.py`).
- Storage is an in-memory `defaultdict(list)`. Nothing is persisted.
- Runs under uvicorn, bound to loopback only.

## The exact port chain

| Hop | Bind / target | Purpose |
|-----|---------------|---------|
| Client → Tor | `127.0.0.1:9050` (SOCKS5) | Client dials `.onion` via the local Tor daemon |
| Tor onion service | virtual port `:80` | Public entry point of the hidden service |
| Onion → nginx | `127.0.0.1:8080` | Reverse proxy, log suppression, timeouts |
| nginx → app | `127.0.0.1:8000` | FastAPI / uvicorn |

## Request/response sequences

### `POST /send` — alice leaves a message for bob

```
alice (Tor client)
  │  POST /send  { "to": "bob", "sender": "alice", "message": "hi bob" }
  ▼
Tor circuit ──► onion :80 ──► nginx :8080 ──► FastAPI :8000
                                                   │
                                                   │  mailboxes["bob"].append({sender, message, timestamp})
                                                   ▼
  ◄──────────────────────────────────────  { "status": "delivered", "to": "bob", "queue_size": 1 }
```

### `GET /inbox/bob` — bob reads his mailbox

```
bob (Tor client)
  │  GET /inbox/bob?pop=1
  ▼
Tor circuit ──► onion :80 ──► nginx :8080 ──► FastAPI :8000
                                                   │
                                                   │  read mailboxes["bob"], then clear it (pop=1)
                                                   ▼
  ◄─────────────  { "client": "bob", "messages": [ {sender:"alice", message:"hi bob", ...} ],
                    "count": 1, "cleared": true }
```

With `pop=0` (the default) the messages come back but stay in the mailbox. A
`DELETE /inbox/bob` clears it explicitly, and `GET /clients` lists the mailboxes
that currently hold pending messages.

## Design rationale

### Why an nginx reverse proxy?
Tor could forward straight to uvicorn, but putting nginx in front buys a few
things:
- **Log suppression** — `access_log off` keeps no request-by-request record.
- **Timeout tuning** — it decouples the app from Tor's latency, so a slow circuit
  doesn't surface as an application error.
- **Header/filtering control** — one place to normalize forwarded headers and,
  if I wanted, filter or rate-limit before anything hits the app.
- **Isolation** — the app only ever talks to a trusted local proxy on loopback.

### Why in-memory storage?
This was a deliberate privacy-by-design / data-minimization decision, not
something left to fix later. Messages live only in RAM. Restart the process and
every mailbox is empty. Nothing touches disk, so there's no at-rest artifact to
seize, subpoena, or leak. The trade-off (no durability, and any live compromise
exposes queued plaintext) is spelled out in `threat-model.md`.

### How the onion address is derived
For a v3 onion service the address encodes the service's public identity key:

```
onion_address = Base32( PUBKEY || CHECKSUM || VERSION ) + ".onion"
  PUBKEY   = 32-byte Ed25519 public key
  CHECKSUM = first 2 bytes of SHA3-256( ".onion checksum" || PUBKEY || VERSION )
  VERSION  = 0x03
```

Those 35 bytes Base32-encode to the familiar 56-character label. Since the
address *is* the public key, there's no separate certificate authority. Checking
that you reached the right service is built into connecting to the address.

### How a client dials the service (client authorization)
1. `gen_client_auth.sh` creates an **x25519** keypair (32 raw bytes / 256-bit,
   Base32-encoded to ~52 characters).
2. The **public** key goes on the server as
   `<HiddenServiceDir>/authorized_clients/<name>.auth` with content
   `descriptor:x25519:<BASE32_PUBLIC_KEY>`, owner `debian-tor`, mode `0600`. Tor
   won't start if the permissions are wrong.
3. The **private** key stays on the client (e.g.
   `~/.local/share/tor/onion_auth/<onion>.auth_private`) and is never shared.
4. The client points its apps at Tor's SOCKS proxy (`127.0.0.1:9050`) using a
   `socks5h://` scheme so that `.onion` resolution happens *inside* Tor. During
   circuit setup Tor uses the client's private key to finish the v3
   client-authorization handshake. Only then does the onion service accept the
   connection. Unauthorized clients get turned away at the Tor layer.
