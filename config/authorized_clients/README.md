# `authorized_clients/`

On the server this directory lives at `<HiddenServiceDir>/authorized_clients/`
(e.g. `/var/lib/tor/onion_api/authorized_clients/`). It holds one `*.auth`
file per authorized client, containing that client's **public** x25519 key:

```
descriptor:x25519:<BASE32_PUBLIC_KEY>
```

Example file `alice.auth`:

```
descriptor:x25519:wd3hi5kbdflmddxpmcom55y7avzcsqpykp5tn3h64lett5jct53a
```

Rules enforced by the tor daemon:

* Owner must be `debian-tor`, permissions **`0600`** (`-rw-------`). Tor refuses
  to start otherwise.
* Only the **public** key goes here. The matching **private** key stays on the
  client machine and is **never** shared or committed.

> No real key files are checked into this repository on purpose. Generate your
> own with [`scripts/gen_client_auth.sh`](../../scripts/gen_client_auth.sh).
