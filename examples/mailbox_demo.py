#!/usr/bin/env python3
"""
Onion Mailbox — client demo
===========================

Exercises the Onion Mailbox REST API end to end:

  1. GET  /health          -> confirm the service is up
  2. POST /send            -> alice leaves a message for bob
  3. GET  /clients         -> list mailboxes with pending messages
  4. GET  /inbox/bob?pop=1 -> bob reads (and clears) his mailbox

Two ways to run it
------------------

* Local (the default): talk straight to a locally running FastAPI app.

      python mailbox_demo.py

* Over Tor: route through the onion service using Tor's SOCKS proxy. Pass the
  onion address (the 56-char v3 label, with or without the ".onion" suffix) and,
  if you want, a custom SOCKS endpoint. This needs `requests[socks]` (PySocks)
  and a running Tor client that's authorized for this onion service.

      python mailbox_demo.py --onion <your-onion-address> --socks 127.0.0.1:9050

  The scheme is `socks5h://` (note the trailing "h"). The "h" makes Tor do the
  .onion resolution, which you need. Resolving it locally would fail and leak a
  DNS lookup.
"""

import argparse
import sys

try:
    import requests
except ImportError:
    sys.exit("This demo needs the 'requests' package: pip install -r requirements.txt")


def build_session(socks: str | None) -> requests.Session:
    """Return a requests Session, optionally routed through a Tor SOCKS proxy."""
    session = requests.Session()
    if socks:
        # socks5h -> hostname/.onion resolution happens at the proxy (inside Tor).
        proxy = f"socks5h://{socks}"
        session.proxies = {"http": proxy, "https": proxy}
    return session


def normalize_base_url(base_url: str, onion: str | None) -> str:
    """If --onion is given, build the onion HTTP base URL; else use --base-url."""
    if onion:
        host = onion.strip()
        if not host.endswith(".onion"):
            host = f"{host}.onion"
        # The onion service exposes virtual port 80, so plain http:// on default port.
        return f"http://{host}"
    return base_url.rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Onion Mailbox API client demo.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Direct base URL for local testing (default: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--onion",
        default=None,
        help="Onion v3 address to reach the service over Tor (overrides --base-url).",
    )
    parser.add_argument(
        "--socks",
        default=None,
        help="Tor SOCKS proxy host:port, e.g. 127.0.0.1:9050 (implied by --onion).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds (Tor can be slow; default: 60).",
    )
    args = parser.parse_args()

    # Routing over Tor requires a SOCKS proxy; default it when --onion is used.
    socks = args.socks
    if args.onion and not socks:
        socks = "127.0.0.1:9050"

    base_url = normalize_base_url(args.base_url, args.onion)
    session = build_session(socks)

    route = f"over Tor via {socks}" if socks else "directly"
    print(f"[*] Target : {base_url}")
    print(f"[*] Routing: {route}\n")

    def request(method: str, path: str, **kwargs):
        url = f"{base_url}{path}"
        resp = session.request(method, url, timeout=args.timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()

    try:
        # 1) Health check
        print("[1] GET /health")
        health = request("GET", "/health")
        print(f"    -> {health}\n")

        # 2) alice sends a message to bob
        print("[2] POST /send  (alice -> bob)")
        payload = {"to": "bob", "sender": "alice", "message": "Hello bob, this is alice over Tor."}
        sent = request("POST", "/send", json=payload)
        print(f"    -> {sent}\n")

        # 3) List mailboxes that currently have pending messages
        print("[3] GET /clients")
        clients = request("GET", "/clients")
        print(f"    -> {clients}\n")

        # 4) bob reads and clears his mailbox (pop=1)
        print("[4] GET /inbox/bob?pop=1")
        inbox = request("GET", "/inbox/bob", params={"pop": 1})
        print(f"    -> {inbox}")
        for i, m in enumerate(inbox.get("messages", []), start=1):
            print(f"       message {i}: from {m['sender']!r}: {m['message']!r}")
        print()

        print("[+] Demo complete.")
        return 0

    except requests.exceptions.RequestException as exc:
        print(f"[!] Request failed: {exc}", file=sys.stderr)
        if socks:
            print(
                "[!] Over Tor: check that the Tor client is running, that this "
                "client is authorized for the onion service, and that "
                "'requests[socks]' (PySocks) is installed.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
