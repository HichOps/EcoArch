#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  EcoArch – Script de déploiement Cloud Run
#  Gère : auto-versioning, test gating, Docker build, Cloud Run deploy
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────
GCP_PROJECT="${GCP_PROJECT_ID:-ecoarch-mvp-1768828854}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-ecoarch-app}"
IMAGE_REPO="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/ecoarch"
IMAGE_NAME="${IMAGE_REPO}/${SERVICE_NAME}"

# Cloud Run settings
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-4}"
MEMORY="${MEMORY:-1Gi}"
CPU="${CPU:-1}"
PORT="${PORT:-8000}"
CONCURRENCY="${CONCURRENCY:-80}"

# ── Couleurs ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${BLUE}[EcoArch]${NC} $*"; }
ok()    { echo -e "${GREEN}[✅]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠️]${NC} $*"; }
fail()  { echo -e "${RED}[❌]${NC} $*"; exit 1; }

# ── 1. Auto-versioning ────────────────────────────────────────────
bump_version() {
    local current
    current=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    log "Version actuelle : ${current}"

    # Extraction major.minor.patch
    local major minor patch
    major=$(echo "$current" | sed 's/^v//' | cut -d. -f1)
    minor=$(echo "$current" | sed 's/^v//' | cut -d. -f2)
    patch=$(echo "$current" | sed 's/^v//' | cut -d. -f3)

    # Bump patch par défaut, ou minor/major via arg
    case "${1:-patch}" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
        *)     patch=$((patch + 1)) ;;
    esac

    VERSION="v${major}.${minor}.${patch}"
    log "Nouvelle version : ${VERSION}"
}

# ── 2. Tests ──────────────────────────────────────────────────────
run_tests() {
    log "Exécution des tests..."

    if ! python3 -m pytest tests/ -v --tb=short 2>&1; then
        fail "Tests échoués – déploiement annulé"
    fi

    ok "Tous les tests passent"
}

# ── 3. Docker Build ───────────────────────────────────────────────
docker_build() {
    log "Build Docker : ${IMAGE_NAME}:${VERSION}"

    docker build \
        --platform linux/amd64 \
        --build-arg VERSION="${VERSION}" \
        -t "${IMAGE_NAME}:${VERSION}" \
        -t "${IMAGE_NAME}:latest" \
        .

    ok "Image construite : ${IMAGE_NAME}:${VERSION}"
}

# ── 4. Docker Push ────────────────────────────────────────────────
docker_push() {
    log "Push vers Artifact Registry..."

    # Authentification si nécessaire
    gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet 2>/dev/null || true

    docker push "${IMAGE_NAME}:${VERSION}"
    docker push "${IMAGE_NAME}:latest"

    ok "Image poussée"
}

# ── 5. Cloud Run Deploy ──────────────────────────────────────────
cloud_run_deploy() {
    log "Déploiement Cloud Run : ${SERVICE_NAME}"

    gcloud run deploy "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --image="${IMAGE_NAME}:${VERSION}" \
        --platform=managed \
        --allow-unauthenticated \
        --port="${PORT}" \
        --memory="${MEMORY}" \
        --cpu="${CPU}" \
        --min-instances="${MIN_INSTANCES}" \
        --max-instances="${MAX_INSTANCES}" \
        --concurrency="${CONCURRENCY}" \
        --set-env-vars="\
GCP_PROJECT_ID=${GCP_PROJECT},\
__REFLEX_SKIP_COMPILE=true,\
__REFLEX_MOUNT_FRONTEND_COMPILED_APP=true,\
REFLEX_BACKEND_ONLY=true,\
APP_VERSION=${VERSION}" \
        --quiet

    ok "Service déployé"

    # Récupérer l'URL
    local url
    url=$(gcloud run services describe "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --format="value(status.url)")

    ok "URL : ${url}"
}

# ── 6. Tag Git ────────────────────────────────────────────────────
git_tag() {
    log "Tag Git : ${VERSION}"

    git tag -a "${VERSION}" -m "Deploy ${VERSION} to Cloud Run" 2>/dev/null || warn "Tag existe déjà"
    git push origin "${VERSION}" 2>/dev/null || warn "Push tag échoué (normal en local)"
}

# ── Main ──────────────────────────────────────────────────────────
main() {
    local bump_type="${1:-patch}"

    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       EcoArch – Pipeline de Déploiement      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    bump_version "${bump_type}"
    run_tests
    docker_build
    docker_push
    cloud_run_deploy
    git_tag

    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Déploiement ${VERSION} terminé avec succès !  ${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════${NC}"
}

# Appel avec le type de bump : major, minor ou patch (default)
main "$@"
