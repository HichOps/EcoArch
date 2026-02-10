# ═══════════════════════════════════════════════════════════════
# EcoArch – Dockerfile de production (single-port granian)
# Build : docker build --build-arg VERSION=v1.1.0 -t ecoarch .
# ═══════════════════════════════════════════════════════════════

# --- Stage 1 : Build (compile le frontend JS) ----------------
FROM python:3.11-slim AS builder
WORKDIR /build

COPY requirements.txt ./
COPY frontend/requirements.txt ./frontend/
RUN pip install --no-cache-dir \
      -r requirements.txt \
      -r frontend/requirements.txt

COPY . .

ARG API_URL=https://ecoarch-app-514436528658.us-central1.run.app
ENV API_URL=${API_URL}

RUN apt-get update && apt-get install -y --no-install-recommends curl unzip && \
    cd /build/frontend && reflex export --frontend-only --no-zip && \
    # Nettoyage : ne garder que .web/build/client (statics compilés)
    rm -rf /build/frontend/.web/node_modules \
           /build/frontend/.web/app \
           /build/frontend/.web/backend \
           /build/frontend/.web/components \
           /build/frontend/.web/public \
           /build/frontend/.web/styles \
           /build/frontend/.web/utils \
           /build/frontend/.web/.next \
           /build/frontend/.web/package*.json && \
    # Supprimer pip du runtime
    pip uninstall -y pip setuptools 2>/dev/null || true

# --- Stage 2 : Runtime (Python pur, pas de Node) -------------
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip gnupg && \
    # --- Terraform ---
    curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main" \
      > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y --no-install-recommends terraform && \
    # --- Infracost ---
    curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh && \
    # Nettoyage apt
    apt-get purge -y curl unzip gnupg && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 ecoarch
USER ecoarch

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copie sélective : uniquement src/ + frontend/
COPY --from=builder --chown=ecoarch:ecoarch /build/src /app/src
COPY --from=builder --chown=ecoarch:ecoarch /build/frontend /app/frontend

ENV PORT=8000 \
    __REFLEX_SKIP_COMPILE=true \
    __REFLEX_MOUNT_FRONTEND_COMPILED_APP=true \
    REFLEX_BACKEND_ONLY=true

ARG VERSION=dev
ENV ECOARCH_VERSION=${VERSION}

EXPOSE 8000
WORKDIR /app/frontend

CMD ["granian", "--host", "0.0.0.0", "--port", "8000", \
     "--interface", "asgi", \
     "--factory", "/app/frontend/frontend/frontend.py:app"]