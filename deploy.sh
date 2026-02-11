#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  EcoArch – Script de déploiement Cloud Run (enrichi)
#
#  Pipeline complet : pré-checks → tests → build → push → deploy
#                     → smoke tests → rollback auto → tag git
#
#  Usage :
#    ./deploy.sh                                 # Full deploy (patch)
#    ./deploy.sh minor                           # Bump minor
#    ./deploy.sh major                           # Bump major
#    ./deploy.sh v2.0.0                          # Version manuelle
#    ./deploy.sh --skip-build                    # Redéploie :latest sans rebuild
#    ./deploy.sh --skip-tests patch              # Hotfix urgent (skip pytest)
#    ./deploy.sh --local                         # Tests + build local uniquement
#    ./deploy.sh --dry-run minor                 # Simulation complète
#    ./deploy.sh --rollback v1.1.1               # Rollback vers une version
#    ./deploy.sh -h | --help                     # Aide
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Chronomètre global ─────────────────────────────────────────────
DEPLOY_START=$(date +%s)

# ── Mode & Options ─────────────────────────────────────────────────
MODE="prod"            # prod | local | dry-run | rollback
BUMP_TYPE="patch"
SKIP_BUILD=false
SKIP_TESTS=false
FORCE_VERSION=""       # vX.Y.Z passé manuellement
ROLLBACK_TARGET=""     # version cible pour rollback
SMOKE_TIMEOUT=20       # secondes d'attente avant smoke test
SMOKE_RETRIES=3        # nombre de tentatives

# ── Secrets attendus dans GCP Secret Manager ───────────────────────
REQUIRED_SECRETS=("supabase-url" "supabase-service-key" "infracost-api-key")

# ── Parsing des arguments ──────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --local)       MODE="local" ;;
        --dry-run)     MODE="dry-run" ;;
        --skip-build)  SKIP_BUILD=true ;;
        --skip-tests)  SKIP_TESTS=true ;;
        --rollback)    MODE="rollback" ;;
        major|minor|patch) BUMP_TYPE="$arg" ;;
        v[0-9]*)
            # Version manuelle (ex: v2.0.0) ou cible rollback
            if [ "$MODE" = "rollback" ]; then
                ROLLBACK_TARGET="$arg"
            else
                FORCE_VERSION="$arg"
            fi
            ;;
        -h|--help)
            cat <<'HELP'
Usage: ./deploy.sh [OPTIONS] [patch|minor|major|vX.Y.Z]

Options :
  (default)       Full pipeline : checks → tests → build → push → deploy → smoke → tag
  --local         Tests + Docker build local uniquement (pas de push/deploy)
  --dry-run       Simulation complète, rien n'est envoyé (preview)
  --skip-build    Redéploie l'image :latest sans rebuild Docker
  --skip-tests    Saute pytest (hotfix urgents uniquement)
  --rollback vX   Rollback Cloud Run vers la version spécifiée
  -h, --help      Affiche cette aide

Versioning :
  patch           Incrémente le patch (v1.1.1 → v1.1.2) [défaut]
  minor           Incrémente le minor (v1.1.1 → v1.2.0)
  major           Incrémente le major (v1.1.1 → v2.0.0)
  v2.0.0          Force une version manuelle

Exemples :
  ./deploy.sh                       # Deploy patch standard
  ./deploy.sh minor                 # Bump minor + deploy
  ./deploy.sh v3.0.0                # Force version + deploy
  ./deploy.sh --skip-tests patch    # Hotfix urgent
  ./deploy.sh --skip-build          # Redéploie sans rebuild
  ./deploy.sh --rollback v1.1.1     # Rollback d'urgence
  ./deploy.sh --local               # Build local de validation
  ./deploy.sh --dry-run major       # Preview d'un bump major
HELP
            exit 0
            ;;
        *) echo "Argument inconnu: $arg (voir --help)"; exit 1 ;;
    esac
done

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

# Variable globale pour l'URL du service (remplie après deploy)
SERVICE_URL=""

# ── Couleurs ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()   { echo -e "${BLUE}[EcoArch]${NC} $*"; }
ok()    { echo -e "${GREEN}[✅]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠️]${NC} $*"; }
fail()  { echo -e "${RED}[❌]${NC} $*"; exit 1; }
dry()   { echo -e "${CYAN}[DRY-RUN]${NC} $*"; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Helpers ────────────────────────────────────────────────────────

elapsed() {
    local end now delta min sec
    now=$(date +%s)
    delta=$((now - DEPLOY_START))
    min=$((delta / 60))
    sec=$((delta % 60))
    echo "${min}m${sec}s"
}

# ══════════════════════════════════════════════════════════════════
# 0. PRÉ-CHECKS (rapport CRIT : vérifier les outils et secrets)
# ══════════════════════════════════════════════════════════════════
preflight_checks() {
    step "0. Pré-checks environnement"

    local errors=0

    # ── Outils requis ──
    for cmd in docker git; do
        if ! command -v "$cmd" &>/dev/null; then
            warn "Commande '$cmd' introuvable"
            errors=$((errors + 1))
        else
            ok "$cmd $(${cmd} --version 2>&1 | head -1 | grep -oP '[\d]+\.[\d]+[\.\d]*' | head -1)"
        fi
    done

    # gcloud (requis seulement en mode prod)
    if [ "$MODE" = "prod" ] || [ "$MODE" = "rollback" ]; then
        if ! command -v gcloud &>/dev/null; then
            fail "'gcloud' introuvable – requis pour le déploiement Cloud Run"
        fi
        ok "gcloud $(gcloud version 2>&1 | head -1 | grep -oP '[\d]+\.[\d]+[\.\d]*' | head -1)"

        # ── Authentification GCP ──
        local account
        account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
        if [ -z "$account" ]; then
            fail "Aucun compte GCP authentifié. Lancez 'gcloud auth login'"
        fi
        ok "GCP auth : ${account}"

        # ── Secrets dans Secret Manager ──
        log "Vérification des secrets GCP Secret Manager..."
        for secret in "${REQUIRED_SECRETS[@]}"; do
            if gcloud secrets describe "$secret" --project="$GCP_PROJECT" &>/dev/null; then
                ok "Secret '${secret}' existe"
            else
                warn "Secret '${secret}' MANQUANT dans le projet ${GCP_PROJECT}"
                errors=$((errors + 1))
            fi
        done
    fi

    # ── Vérification git propre (avertissement seulement) ──
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        warn "Modifications non committées détectées (git status non propre)"
    else
        ok "Git working tree propre"
    fi

    if [ "$errors" -gt 0 ]; then
        fail "${errors} pré-check(s) en échec – corrigez avant de déployer"
    fi

    ok "Tous les pré-checks passent"
}

# ══════════════════════════════════════════════════════════════════
# 1. AUTO-VERSIONING
# ══════════════════════════════════════════════════════════════════
bump_version() {
    step "1. Versioning"

    # Version manuelle forcée
    if [ -n "$FORCE_VERSION" ]; then
        VERSION="$FORCE_VERSION"
        log "Version manuelle forcée : ${VERSION}"
        return
    fi

    local current
    current=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    log "Version actuelle : ${current}"

    local major minor patch
    major=$(echo "$current" | sed 's/^v//' | cut -d. -f1)
    minor=$(echo "$current" | sed 's/^v//' | cut -d. -f2)
    patch=$(echo "$current" | sed 's/^v//' | cut -d. -f3)

    case "${1:-patch}" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
        *)     patch=$((patch + 1)) ;;
    esac

    VERSION="v${major}.${minor}.${patch}"
    log "Nouvelle version : ${VERSION}"
}

# ══════════════════════════════════════════════════════════════════
# 2. TESTS
# ══════════════════════════════════════════════════════════════════
run_tests() {
    step "2. Tests"

    if [ "$SKIP_TESTS" = true ]; then
        warn "Tests ignorés (--skip-tests) – UNIQUEMENT pour hotfix urgents"
        return
    fi

    log "Exécution de pytest..."

    if ! python3 -m pytest tests/ -v --tb=short 2>&1; then
        fail "Tests échoués – déploiement annulé"
    fi

    ok "Tous les tests passent"
}

# ══════════════════════════════════════════════════════════════════
# 3. DOCKER BUILD
# ══════════════════════════════════════════════════════════════════
docker_build() {
    step "3. Docker Build"

    if [ "$SKIP_BUILD" = true ]; then
        warn "Build ignoré (--skip-build) – utilisation de l'image :latest"
        return
    fi

    if [ "$MODE" = "dry-run" ]; then
        dry "docker build --platform linux/amd64 --build-arg VERSION=${VERSION} -t ${IMAGE_NAME}:${VERSION} ."
        return
    fi

    log "Build Docker : ${IMAGE_NAME}:${VERSION}"
    local build_start
    build_start=$(date +%s)

    docker build \
        --platform linux/amd64 \
        --build-arg VERSION="${VERSION}" \
        -t "${IMAGE_NAME}:${VERSION}" \
        -t "${IMAGE_NAME}:latest" \
        .

    local build_duration=$(( $(date +%s) - build_start ))
    ok "Image construite en ${build_duration}s : ${IMAGE_NAME}:${VERSION}"

    # ── Reporting taille image ──
    local image_size
    image_size=$(docker image inspect "${IMAGE_NAME}:${VERSION}" \
        --format='{{.Size}}' 2>/dev/null || echo "0")
    if [ "$image_size" -gt 0 ]; then
        local size_mb=$((image_size / 1024 / 1024))
        log "Taille image : ${size_mb} MB"
        if [ "$size_mb" -gt 800 ]; then
            warn "Image > 800 MB – vérifiez les dépendances inutiles"
        elif [ "$size_mb" -lt 400 ]; then
            ok "Image compacte (< 400 MB)"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════
# 4. DOCKER PUSH
# ══════════════════════════════════════════════════════════════════
docker_push() {
    step "4. Docker Push"

    if [ "$MODE" != "prod" ]; then
        [ "$MODE" = "dry-run" ] && dry "docker push ${IMAGE_NAME}:${VERSION}"
        [ "$MODE" = "local" ]   && warn "Mode local – push ignoré"
        return
    fi

    log "Push vers Artifact Registry..."

    gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet 2>/dev/null || true

    if [ "$SKIP_BUILD" = true ]; then
        docker push "${IMAGE_NAME}:latest"
        ok "Image :latest poussée"
    else
        docker push "${IMAGE_NAME}:${VERSION}"
        docker push "${IMAGE_NAME}:latest"
        ok "Images ${VERSION} + :latest poussées"
    fi
}

# ══════════════════════════════════════════════════════════════════
# 5. CLOUD RUN DEPLOY
# ══════════════════════════════════════════════════════════════════
cloud_run_deploy() {
    step "5. Cloud Run Deploy"

    if [ "$MODE" != "prod" ]; then
        [ "$MODE" = "dry-run" ] && dry "gcloud run deploy ${SERVICE_NAME} --image=${IMAGE_NAME}:${VERSION} --region=${GCP_REGION}"
        [ "$MODE" = "local" ]   && warn "Mode local – deploy Cloud Run ignoré"
        return
    fi

    local deploy_image="${IMAGE_NAME}:${VERSION}"
    if [ "$SKIP_BUILD" = true ]; then
        deploy_image="${IMAGE_NAME}:latest"
        log "Déploiement de l'image :latest (--skip-build)"
    fi

    log "Déploiement Cloud Run : ${SERVICE_NAME}"

    gcloud run deploy "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --image="${deploy_image}" \
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

    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --format="value(status.url)")

    ok "URL : ${SERVICE_URL}"
}

# ══════════════════════════════════════════════════════════════════
# 6. SMOKE TESTS (rapport : curl /ping et /)
# ══════════════════════════════════════════════════════════════════
smoke_tests() {
    step "6. Smoke Tests"

    if [ "$MODE" != "prod" ]; then
        [ "$MODE" = "dry-run" ] && dry "curl -sf ${SERVICE_URL:-https://...}/ping && curl -sf ${SERVICE_URL:-https://...}/"
        [ "$MODE" = "local" ]   && warn "Mode local – smoke tests ignorés"
        return
    fi

    if [ -z "$SERVICE_URL" ]; then
        warn "URL du service inconnue – smoke tests ignorés"
        return
    fi

    log "Attente ${SMOKE_TIMEOUT}s pour le cold start..."
    sleep "$SMOKE_TIMEOUT"

    local endpoints=("/ping" "/")
    local all_passed=true

    for endpoint in "${endpoints[@]}"; do
        local url="${SERVICE_URL}${endpoint}"
        local attempt=1
        local success=false

        while [ "$attempt" -le "$SMOKE_RETRIES" ]; do
            log "Test ${url} (tentative ${attempt}/${SMOKE_RETRIES})..."

            local http_code body_size
            http_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
            body_size=$(curl -sf -o /dev/null -w "%{size_download}" --max-time 10 "$url" 2>/dev/null || echo "0")

            if [ "$http_code" = "200" ]; then
                ok "${endpoint} → HTTP ${http_code} (${body_size} bytes)"
                success=true
                break
            fi

            warn "${endpoint} → HTTP ${http_code} (tentative ${attempt})"
            attempt=$((attempt + 1))
            [ "$attempt" -le "$SMOKE_RETRIES" ] && sleep 5
        done

        if [ "$success" = false ]; then
            warn "ÉCHEC smoke test pour ${endpoint} après ${SMOKE_RETRIES} tentatives"
            all_passed=false
        fi
    done

    if [ "$all_passed" = false ]; then
        return 1
    fi

    ok "Smoke tests réussis"
    return 0
}

# ══════════════════════════════════════════════════════════════════
# 7. ROLLBACK AUTOMATIQUE
# ══════════════════════════════════════════════════════════════════
rollback() {
    local target_version="$1"
    step "ROLLBACK vers ${target_version}"

    if [ "$MODE" = "dry-run" ]; then
        dry "gcloud run deploy ${SERVICE_NAME} --image=${IMAGE_NAME}:${target_version}"
        return
    fi

    log "Rollback Cloud Run vers ${IMAGE_NAME}:${target_version}..."

    gcloud run deploy "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --image="${IMAGE_NAME}:${target_version}" \
        --platform=managed \
        --allow-unauthenticated \
        --port="${PORT}" \
        --memory="${MEMORY}" \
        --cpu="${CPU}" \
        --min-instances="${MIN_INSTANCES}" \
        --max-instances="${MAX_INSTANCES}" \
        --concurrency="${CONCURRENCY}" \
        --quiet

    ok "Rollback vers ${target_version} terminé"

    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
        --project="${GCP_PROJECT}" \
        --region="${GCP_REGION}" \
        --format="value(status.url)")

    ok "URL : ${SERVICE_URL}"
}

# ══════════════════════════════════════════════════════════════════
# 8. GIT TAG
# ══════════════════════════════════════════════════════════════════
git_tag() {
    step "8. Git Tag"

    if [ "$MODE" != "prod" ]; then
        [ "$MODE" = "dry-run" ] && dry "git tag -a ${VERSION} -m 'Deploy ${VERSION}'"
        [ "$MODE" = "local" ]   && log "Version ${VERSION} (local only, pas de tag/push)"
        return
    fi

    log "Tag Git : ${VERSION}"

    git tag -a "${VERSION}" -m "Deploy ${VERSION} to Cloud Run" 2>/dev/null || warn "Tag existe déjà"
    git push origin "${VERSION}" 2>/dev/null || warn "Push tag échoué (normal si pas de remote)"
}

# ══════════════════════════════════════════════════════════════════
# 9. RAPPORT FINAL
# ══════════════════════════════════════════════════════════════════
print_summary() {
    local total_elapsed
    total_elapsed=$(elapsed)

    echo ""
    echo -e "${BOLD}── Résumé du déploiement ──${NC}"
    echo -e "  Version     : ${GREEN}${VERSION}${NC}"
    echo -e "  Mode        : ${MODE}"
    echo -e "  Durée       : ${total_elapsed}"
    [ -n "$SERVICE_URL" ] && echo -e "  URL         : ${SERVICE_URL}"
    echo ""
}

# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       EcoArch – Pipeline de Déploiement          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$MODE" != "prod" ]; then
        echo -e "  ${CYAN}Mode : ${MODE} | Bump : ${BUMP_TYPE}${NC}"
        echo ""
    fi

    # ── Mode Rollback (circuit court) ──
    if [ "$MODE" = "rollback" ]; then
        if [ -z "$ROLLBACK_TARGET" ]; then
            fail "Usage: ./deploy.sh --rollback vX.Y.Z"
        fi
        VERSION="$ROLLBACK_TARGET"
        preflight_checks
        rollback "$ROLLBACK_TARGET"
        if ! smoke_tests; then
            fail "Smoke tests échoués après rollback – intervention manuelle requise"
        fi
        print_summary
        return
    fi

    # ── Pipeline standard ──
    preflight_checks
    bump_version "${BUMP_TYPE}"
    run_tests
    docker_build
    docker_push
    cloud_run_deploy

    # ── Smoke tests + rollback auto si échec ──
    if [ "$MODE" = "prod" ]; then
        # Sauvegarder la version précédente pour rollback potentiel
        local previous_version
        previous_version=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

        if ! smoke_tests; then
            warn "Smoke tests échoués pour ${VERSION}"

            if [ -n "$previous_version" ] && [ "$previous_version" != "$VERSION" ]; then
                warn "Rollback automatique vers ${previous_version}..."
                rollback "$previous_version"

                if smoke_tests; then
                    ok "Rollback vers ${previous_version} validé par smoke tests"
                else
                    warn "Rollback smoke tests aussi en échec – intervention manuelle requise"
                fi

                fail "Déploiement ${VERSION} ANNULÉ – rollback vers ${previous_version}"
            else
                fail "Smoke tests échoués et pas de version précédente pour rollback"
            fi
        fi
    fi

    git_tag
    print_summary

    if [ "$MODE" = "dry-run" ]; then
        echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}  Dry-run ${VERSION} terminé (aucune action réelle)${NC}"
        echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
    elif [ "$MODE" = "local" ]; then
        echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Build local ${VERSION} OK – prêt pour la prod    ${NC}"
        echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
    else
        echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Déploiement ${VERSION} terminé avec succès !     ${NC}"
        echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
    fi
}

main
