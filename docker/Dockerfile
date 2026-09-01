# Builds the FastAPI Onion Mailbox application image.
#
# Build context is the repository root (see docker-compose.yml: `context: ..`),
# so paths below are relative to 05-tor-onion-service/.
FROM python:3.12-slim

WORKDIR /srv

# Install dependencies first so the layer is cached across app-code changes.
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app/ ./app/

EXPOSE 8000

# NOTE on the bind address:
#   On bare metal the app is bound to 127.0.0.1 (loopback only), because it must
#   never be reachable except through the local nginx -> Tor onion service chain.
#   Inside a container, 127.0.0.1 refers to the container itself, so the nginx
#   container could not reach it. Here we bind 0.0.0.0 *inside the container* and
#   rely on Docker network isolation instead: the api service publishes NO host
#   port (see docker-compose.yml), so it is reachable only from other services on
#   the internal Compose network, never from the host or the internet.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "app"]
