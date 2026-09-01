"""
Onion Mailbox API
=================

A small message-exchange REST API meant to run behind a Tor v3 Onion Service.
Two authorized clients (say "alice" and "bob") drop messages into server-side
mailboxes and read them back, without ever revealing their IP addresses to each
other or to the server.

Notes
-----
* Storage is in-memory only (a `defaultdict`). Nothing hits disk, so on restart
  every mailbox is empty. That's a deliberate data-minimization choice, not
  something to fix later.
* Access control does not live here. It's enforced one layer down by Tor v3
  client authorization (x25519 keys): only clients holding an authorized private
  key can reach the .onion address at all. See ../docs/threat-model.md for what
  that does and doesn't cover.
* The service binds to 127.0.0.1 only, and is reached through:
      Tor  :80  ->  nginx  127.0.0.1:8080  ->  uvicorn/FastAPI  127.0.0.1:8000

Run locally:
    uvicorn app:app --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
import time
from collections import defaultdict

app = FastAPI(title="Onion Mailbox API")

# ============ MAILBOX STORAGE (in-memory) ============
# Format: mailboxes["alice"] = [{"sender": "bob", "message": "...", "timestamp": ...}, ...]
mailboxes = defaultdict(list)


# ============ MODELS ============
class Message(BaseModel):
    to: str
    sender: str
    message: str


# ============ BASIC ENDPOINTS ============
@app.get("/status")
def status():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "onion-mailbox-api"}


@app.get("/slow")
def slow(ms: int = Query(default=800, ge=0, le=60000)):
    """Artificial-latency endpoint used to benchmark round-trip time over Tor."""
    time.sleep(ms / 1000.0)
    return {"status": "ok", "slept_ms": ms}


# ============ MAILBOX ENDPOINTS ============
@app.post("/send")
def send_message(msg: Message):
    """Client A leaves a message for Client B in B's mailbox."""
    mailboxes[msg.to].append({
        "sender": msg.sender,
        "message": msg.message,
        "timestamp": time.time(),
    })
    return {
        "status": "delivered",
        "to": msg.to,
        "queue_size": len(mailboxes[msg.to]),
    }


@app.get("/inbox/{client_id}")
def get_inbox(client_id: str, pop: int = Query(default=0, ge=0, le=1)):
    """Read a client's messages. pop=1 also clears the mailbox after reading."""
    if client_id not in mailboxes:
        return {"client": client_id, "messages": [], "count": 0}

    messages = mailboxes[client_id]
    count = len(messages)

    if pop == 1:
        # Return and empty the mailbox
        result = list(messages)
        mailboxes[client_id] = []
        return {"client": client_id, "messages": result, "count": count, "cleared": True}

    return {"client": client_id, "messages": list(messages), "count": count}


@app.get("/clients")
def list_clients():
    """List clients that currently have pending messages."""
    return {
        "clients": {k: len(v) for k, v in mailboxes.items() if v},
        "total_mailboxes": len(mailboxes),
    }


@app.delete("/inbox/{client_id}")
def clear_inbox(client_id: str):
    """Manually empty a client's mailbox."""
    if client_id in mailboxes:
        count = len(mailboxes[client_id])
        mailboxes[client_id] = []
        return {"status": "cleared", "client": client_id, "deleted_messages": count}
    return {"status": "not_found", "client": client_id}
