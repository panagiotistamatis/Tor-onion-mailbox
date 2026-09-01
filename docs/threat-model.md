# Threat Model

A threat model for the Onion Mailbox service. This is an academic proof of
concept, and one of the things I actually wanted to get right was being precise
about what the design protects and what it doesn't. Overselling the guarantees
would defeat the purpose, so I've kept the limitations below plain.

## Assets

| Asset | Why it matters |
|-------|----------------|
| **Server location / IP** | Deanonymizing the host would expose where the service runs and who operates it. |
| **Client identities** | Which parties (`alice`, `bob`) participate, and their network location. |
| **Message contents** | The confidentiality of messages in transit and while queued. |
| **Access control** | The guarantee that only authorized clients can reach the service at all. |

## Adversaries

- **Network observer / ISP (local passive).** Can see packets on the client's or
  server's link. They see only Tor traffic: encrypted, no readable HTTP, no
  server IP, no DNS queries. I confirmed this with Wireshark.
- **Global passive adversary (the hard case).** Tor's own threat model doesn't
  defend against someone who can watch a large fraction of the network and do
  end-to-end traffic correlation and timing analysis. This design inherits that
  limitation and doesn't try to beat global correlation.
- **Unauthorized would-be client.** An outsider who wants in but holds no
  authorized key. Blocked at the Tor layer by v3 client authorization. They can't
  complete a circuit to the onion service, so they never reach HTTP.
- **Malicious authorized client.** Someone who holds a *valid* client key but
  behaves dishonestly. This is the weakest spot in the current design (see below).

## What this design protects

- **Server IP anonymity.** The host is only reachable as a `.onion`. Its real IP
  is never published and never appears on the wire (in Wireshark,
  source/destination are only `127.0.0.1` locally, and Tor-encrypted otherwise).
- **Transport encryption (Wireshark-verified).** All the captured traffic is
  encrypted ciphertext. No plaintext HTTP, no readable `Host`/`GET`/`POST` lines.
- **Access control via Tor v3 client authorization.** Only clients whose public
  x25519 key is registered on the server can open a circuit. The check happens
  *below* the application, so unauthorized parties never touch the API surface.
- **No DNS leakage.** `.onion` names resolve through Tor's distributed hash
  table, not DNS, so no DNS query for the service is ever emitted.

## What this design does NOT protect

- **The app doesn't authenticate the `sender` field.** `POST /send` carries a
  self-declared `sender` string, and the app trusts it as-is. A malicious
  authorized client could set `sender` to any name and spoof someone else. Tor
  authorizes *that a client is allowed in*, not *who they claim to be inside the
  message*. There's no binding between the Tor client identity and the
  application-level sender.
- **No end-to-end message signing or encryption above Tor.** Confidentiality and
  integrity ride entirely on the Tor transport. Messages are plaintext to the
  server and to anyone with access to the server process. There's no per-message
  signature to catch tampering or prove who wrote a message.
- **In-memory store means no durability, and compromise exposes plaintext.**
  Messages live only in RAM. A restart wipes everything (that's on purpose), but
  while the process is running, any compromise of the host or the Python process
  exposes every queued message in cleartext.
- **No rate limiting or replay protection at the app layer.** An authorized
  client can flood `/send`, and there's no nonce or sequence mechanism to reject
  replayed requests.

## Trust assumptions

- The **Tor network** works as designed and isn't compromised by a global passive
  adversary doing traffic correlation.
- The **server host** is trusted and uncompromised. The onion service private
  keys and the `authorized_clients/` directory stay secret and correctly
  permissioned (`0600`, owner `debian-tor`).
- **Authorized clients keep their private keys secret.** A leaked client key gives
  an attacker the same access as that client.
- **Authorized clients are semi-trusted.** They're allowed in, but the design
  doesn't defend one authorized client against another at the application layer.

## Residual risks

- Traffic-correlation / timing attacks by a sufficiently global adversary
  (outside Tor's threat model).
- Sender spoofing and message tampering by a malicious authorized client.
- Plaintext exposure of queued messages if the running server is compromised.
- Denial of service from a flooding authorized client (no app-layer rate
  limiting).
- Metadata inference from message timing and volume, even without reading
  contents.

## Future work

- **End-to-end message signing** (e.g. Ed25519 per-client signatures) to bind the
  `sender` field to a real identity and detect tampering.
- **End-to-end encryption** of message contents so the server never sees
  plaintext.
- A real **client application** (React/Vue) instead of a demo script.
- **Encrypted persistence** if durability is ever needed, keeping
  data-minimization as the default.
- **Rate limiting and replay protection** at the application layer.
