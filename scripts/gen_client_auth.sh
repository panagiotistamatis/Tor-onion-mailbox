#!/usr/bin/env bash
#
# Generate a Tor v3 onion-service client-authorization key pair (x25519).
#
#   ./gen_client_auth.sh alice
#
# Produces:
#   * alice.auth          -> PUBLIC key line; copy to the SERVER at
#                            <HiddenServiceDir>/authorized_clients/alice.auth (chmod 600)
#   * alice.auth_private  -> PRIVATE key line; keep on the CLIENT at
#                            ~/.local/share/tor/onion_auth/  (NEVER share/commit)
#
# Requires: openssl, basez (or base32).  Tested on Debian/Kali.
set -euo pipefail

NAME="${1:?usage: gen_client_auth.sh <client-name>}"
ONION="${2:-<your-onion-address-without-.onion>}"

# 1) Generate an x25519 private key and derive the public key.
openssl genpkey -algorithm x25519 -out "/tmp/${NAME}_x25519.pem" 2>/dev/null

# 2) Base32-encode both halves the way Tor expects (32 raw bytes -> 52 chars, no padding).
priv_raw=$(openssl pkey -in "/tmp/${NAME}_x25519.pem" -text_pub \
  | grep -A3 "priv:" | tail -n +2 | tr -d ' \n:' | head -c 64)
pub_raw=$(openssl pkey -in "/tmp/${NAME}_x25519.pem" -text_pub \
  | grep -A3 "pub:"  | tail -n +2 | tr -d ' \n:' | head -c 64)

b32() { python3 -c "import base64,sys; print(base64.b32encode(bytes.fromhex(sys.argv[1])).decode().rstrip('=').upper())" "$1"; }

PRIV_B32=$(b32 "$priv_raw")
PUB_B32=$(b32 "$pub_raw")

# 3) Write the two files.
echo "descriptor:x25519:${PUB_B32}" > "${NAME}.auth"
echo "${ONION}:descriptor:x25519:${PRIV_B32}" > "${NAME}.auth_private"
chmod 600 "${NAME}.auth" "${NAME}.auth_private"
rm -f "/tmp/${NAME}_x25519.pem"

cat <<EOF

Generated client authorization for "${NAME}":
  PUBLIC  -> ${NAME}.auth          (deploy on SERVER, chmod 600)
  PRIVATE -> ${NAME}.auth_private  (keep on CLIENT, keep secret)

Never commit ${NAME}.auth_private to version control.
EOF
