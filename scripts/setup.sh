#!/usr/bin/env bash
#
# End-to-end setup for the Tor Onion Mailbox service on Debian/Ubuntu.
# Run as root (or with sudo). Idempotent-ish: safe to re-run.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HS_DIR="/var/lib/tor/onion_api"

echo "[*] Installing tor, nginx and python..."
apt-get update -qq
apt-get install -y tor nginx python3 python3-venv python3-pip

echo "[*] Deploying nginx reverse proxy..."
install -m 0644 "$REPO_DIR/config/nginx/onion_api.conf" /etc/nginx/sites-available/onion_api.conf
ln -sf /etc/nginx/sites-available/onion_api.conf /etc/nginx/sites-enabled/onion_api.conf
nginx -t && systemctl reload nginx

echo "[*] Configuring the Tor v3 onion service..."
grep -q "^HiddenServiceDir $HS_DIR" /etc/tor/torrc || cat "$REPO_DIR/config/torrc" >> /etc/tor/torrc
systemctl restart tor
sleep 5

if [[ -f "$HS_DIR/hostname" ]]; then
  echo "[+] Onion address: $(cat "$HS_DIR/hostname")"
else
  echo "[!] hostname not created yet; check: journalctl -u tor -n 50"
fi

echo "[*] Installing the FastAPI application..."
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install -q -r "$REPO_DIR/app/requirements.txt"

echo
echo "[+] Setup complete. Start the API with:"
echo "    $REPO_DIR/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --app-dir $REPO_DIR/app"
echo
echo "    Then add authorized clients with scripts/gen_client_auth.sh and place"
echo "    each <client>.auth into $HS_DIR/authorized_clients/ (chmod 600)."
