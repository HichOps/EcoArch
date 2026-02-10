# 📋 Rapport de Déploiement — EcoArch v1.1.1

**Date** : 10 février 2026  
**URL de production** : https://ecoarch-app-514436528658.us-central1.run.app  
**Révision Cloud Run** : `ecoarch-app-00020-gjv`  
**Projet GCP** : `ecoarch-mvp-1768828854`  
**Région** : `us-central1`

---

## 1. Contexte initial

L'application EcoArch (Reflex 0.8.26 / Python 3.11) ne fonctionnait pas en production sur Cloud Run. Les tentatives de déploiement échouaient systématiquement (7 révisions en échec : `00006` → `00012`). L'image Docker était volumineuse (1.16 GB), non optimisée, et le processus de déploiement n'était ni documenté ni reproductible.

### Problèmes identifiés

| # | Problème | Impact |
|---|----------|--------|
| 1 | `reflex run --backend-only` ne sert pas les fichiers statiques (frontend) | `/` retourne 404 en prod |
| 2 | Vite dev server (port 3000) incompatible avec Cloud Run (single-port) | Conflit de ports, timeout au démarrage |
| 3 | Recompilation frontend à chaque cold start (~30s) | Timeout Cloud Run (health check échoué) |
| 4 | `node_modules` (224 MB) embarqué dans l'image runtime | Image 763 MB → 1.16 GB |
| 5 | Dépendances Python inutiles : pandas, numpy, plotly, google-cloud-storage | +236 MB dans l'image |
| 6 | `db_url` dans `rxconfig.py` référence `DATABASE_URL` jamais définie | Erreur potentielle au boot |
| 7 | `requests` utilisé dans le code mais absent de `requirements.txt` | Marche par chance (dépendance transitive) |
| 8 | Multiples Dockerfiles (`Dockerfile`, `Dockerfile.prod`), scripts obsolètes (`deploy/`) | Confusion, erreurs de CI |
| 9 | Volume mount `- .:/app` en docker-compose écrase le code conteneur | Conflits fichiers en dev |
| 10 | Binaires `infracost` et `terraform` absents de l'image optimisée | Simulation impossible (`[Errno 2]`) |
| 11 | Aucun script de déploiement standardisé | Commandes manuelles, erreurs fréquentes |

---

## 2. Découverte clé : Granian direct avec env vars internes Reflex

Après analyse du code source de Reflex 0.8.26, la solution trouvée consiste à **appeler granian directement** (sans passer par `reflex run`) avec trois variables d'environnement internes :

```bash
# ⚠️ Double underscore __ (convention interne Reflex)
__REFLEX_SKIP_COMPILE=true
__REFLEX_MOUNT_FRONTEND_COMPILED_APP=true

# Simple préfixe (pas de double underscore)
REFLEX_BACKEND_ONLY=true
```

**Commande de lancement :**
```bash
granian --host 0.0.0.0 --port 8000 --interface asgi \
        --factory /app/frontend/frontend/frontend.py:app
```

Cela permet de :
- Servir le backend (WebSocket + API) ET le frontend compilé sur un **seul port** (8000)
- Éviter toute recompilation au démarrage (cold start < 3s)
- Ne pas nécessiter Node.js en runtime

---

## 3. Modifications effectuées

### 3.1. `Dockerfile` (réécriture complète)

**Avant** : un seul stage, installation Node.js + `reflex run`, 1.16 GB.

**Après** : multi-stage optimisé.

```dockerfile
# Stage 1 — Builder : compile le frontend JS
FROM python:3.11-slim AS builder
WORKDIR /build

COPY requirements.txt ./
COPY frontend/requirements.txt ./frontend/
RUN pip install --no-cache-dir -r requirements.txt -r frontend/requirements.txt

COPY . .
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip && \
    cd /build/frontend && reflex export --frontend-only --no-zip && \
    rm -rf /build/frontend/.web/node_modules \
           /build/frontend/.web/app \
           /build/frontend/.web/backend \
           /build/frontend/.web/components \
           /build/frontend/.web/public \
           /build/frontend/.web/styles \
           /build/frontend/.web/utils \
           /build/frontend/.web/.next \
           /build/frontend/.web/package*.json && \
    pip uninstall -y pip setuptools 2>/dev/null || true

# Stage 2 — Runtime : Python pur + terraform + infracost (pas de Node)
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip gnupg && \
    # Terraform
    curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main" \
      > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y --no-install-recommends terraform && \
    # Infracost
    curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh && \
    apt-get purge -y curl unzip gnupg && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 ecoarch
USER ecoarch

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=ecoarch:ecoarch /build/src /app/src
COPY --from=builder --chown=ecoarch:ecoarch /build/frontend /app/frontend

ENV PORT=8000 \
    __REFLEX_SKIP_COMPILE=true \
    __REFLEX_MOUNT_FRONTEND_COMPILED_APP=true \
    REFLEX_BACKEND_ONLY=true

WORKDIR /app/frontend
CMD ["granian", "--host", "0.0.0.0", "--port", "8000", \
     "--interface", "asgi", "--factory", "/app/frontend/frontend/frontend.py:app"]
```

**Points clés :**
- `reflex export --frontend-only --no-zip` dans le builder → pré-compile les statics
- Nettoyage agressif de `.web/` (ne garde que `build/client/`)
- Copie sélective : seuls `src/` et `frontend/` vont dans le runtime
- User non-root `ecoarch` (UID 1000)
- `terraform` + `infracost` installés pour le simulateur

---

### 3.2. `requirements.txt` (nettoyage dépendances)

**Supprimé (6 paquets, ~236 MB)** :
- `pandas` — jamais importé nulle part dans le code
- `numpy` — jamais importé
- `plotly` — jamais importé
- `google-cloud-storage` — jamais importé
- `pytest` / `pytest-mock` — dépendances de dev, déplacées dans `requirements-dev.txt`

**Ajouté** :
- `requests` — utilisé dans `src/gitlab_comment.py` mais non déclaré

**Version finale** :
```
reflex>=0.6.0
python-dotenv
supabase
google-cloud-secret-manager
requests
celery[redis]>=5.3.0
redis>=5.0.0
```

---

### 3.3. `frontend/rxconfig.py` (correction)

**Avant** :
```python
config = rx.Config(
    app_name="frontend",
    db_url=os.getenv("DATABASE_URL"),  # ← jamais défini nulle part
    api_url=os.getenv("API_URL", "https://ecoarch-app-..."),
)
```

**Après** :
```python
config = rx.Config(
    app_name="frontend",
    api_url=os.getenv(
        "API_URL",
        "https://ecoarch-app-514436528658.us-central1.run.app",
    ),
)
```

**Raison** : `db_url` référençait `DATABASE_URL` qui n'est définie nulle part (ni en .env, ni en secrets, ni en vars Cloud Run). Paramètre mort qui risquait de produire une erreur Alembic/SQLAlchemy au démarrage.

---

### 3.4. `.dockerignore` (réécriture restrictive)

Avant : fichier minimal. Après : exclusion stricte de tout ce qui n'a pas sa place dans l'image :

```
__pycache__/  *.pyc  venv/  .pytest_cache/
frontend/.web/  frontend/.states/  node_modules/
.git/  .gitignore  .gitlab-ci.yml
.env  .env.*  !.env.example  gcp-key.json*       # ← SÉCURITÉ
*.md  *.html  rapport_EcoArch.py
tests/  infra/  requirements-dev.txt
Dockerfile  docker-compose*.yml  deploy.sh
```

**Impact sécurité** : `gcp-key.json*` et `.env` ne seront JAMAIS copiés dans l'image Docker, même par erreur.

---

### 3.5. `docker-compose.yml` (nettoyage dev local)

| Modification | Avant | Après | Raison |
|---|---|---|---|
| `container_name` | `ecoarch_v9_container` | `ecoarch_dev` | Nom clair |
| Volume `.:/app` | Présent | **Supprimé** | Écrasait le code du conteneur |
| `REDIS_URL` | `redis://redis:6379` | `redis://redis:6379/0` | DB explicite |
| Image Redis | `redis:alpine` | `redis:7-alpine` | Version pinée |
| `API_URL` | Absent | `http://localhost:8000` | Requis pour Reflex |

---

### 3.6. `.env.example` (documentation complète)

Toutes les variables d'environnement nécessaires sont maintenant documentées :

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here
GCP_PROJECT_ID=ecoarch-mvp-1768828854
API_URL=http://localhost:8000
INFRACOST_API_KEY=your-infracost-api-key
INFRACOST_TIMEOUT=30
REDIS_URL=redis://redis:6379/0
BUDGET_LIMIT=50.0
```

---

### 3.7. `deploy.sh` (nouveau — script de déploiement industrialisé)

Script bash complet créé à la racine du projet :

**Fonctionnalités** :
- **Auto-versioning** : lit le dernier git tag, incrémente le patch (`v1.1.0` → `v1.1.1`)
- **Version manuelle** : `./deploy.sh v2.0.0`
- **Skip build** : `./deploy.sh --skip-build` (redéploie la dernière image)
- **Pré-checks** : vérifie docker, gcloud auth, existence des 3 secrets
- **Build** : injecte `API_URL` et `VERSION` comme build args
- **Deploy** : Cloud Run avec tous les env vars + secrets pinés à `:1`
- **Smoke test** : attend 15s puis curl `/ping` et `/` (doit retourner 200)
- **Tag git** : crée automatiquement le tag de version

---

### 3.8. Fichiers supprimés

| Fichier/Dossier | Raison |
|---|---|
| `Dockerfile` (ancien) | Remplacé par la réécriture de `Dockerfile.prod` → renommé `Dockerfile` |
| `deploy/` | Dossier entier de scripts obsolètes |
| `docker-compose.prod.yml` | Redondant avec Cloud Run |
| `rapport_EcoArch.py` | Script one-shot, plus utilisé |
| `Rapport_EcoArch_V10.html` | Rapport statique ancien |
| `REFACTORING.md` | Notes de refactoring terminées |
| `gcp-key.json:Zone.Identifier` | Artefact Windows (WSL) |

---

## 4. Historique des révisions Cloud Run

| Révision | Version | Statut | Problème |
|---|---|---|---|
| `00006-g7t` | — | ❌ | Image not found (build échoué) |
| `00007` → `00012` | — | ❌ | Port conflicts (Vite 3000 vs 8000), recompilation timeout |
| `00013` → `00016` | — | ❌ | `--backend-only` → 404 sur `/`, statics non servis |
| `00017-7ql` | v1.0.0 | ✅ | **Breakthrough** : granian direct + env vars internes |
| `00018-jwp` | v1.1.0 | ❌ | `.web/build/client` absent (reflex export avait besoin de `unzip`) |
| `00019-wfw` | v1.1.0 | ✅ | Fix : ajout `unzip` pour bun dans le builder |
| **`00020-gjv`** | **v1.1.1** | ✅ | Fix : ajout `terraform` + `infracost` dans le runtime |

---

## 5. Résultats

### 5.1. Taille de l'image

| Version | Taille | Détail |
|---|---|---|
| Première tentative | 1.16 GB | Node.js + tous les packages + node_modules |
| v1.0.0 | 763 MB | Granian direct mais packages inutiles + node_modules |
| v1.1.0 (sans CLI) | 334 MB | Optimisé mais sans terraform/infracost |
| **v1.1.1 (finale)** | **642 MB** | Avec terraform (~170 MB) + infracost (~130 MB) |

> Les 300 MB de terraform + infracost sont **incompressibles** — ce sont les binaires Go nécessaires à la fonctionnalité cœur de simulation.

### 5.2. Smoke tests en production

```
/ping  → HTTP 200 (0.35s)
/      → HTTP 200, 46 134 bytes (0.62s)
```

### 5.3. Cold start

| Métrique | Avant | Après |
|---|---|---|
| Cold start | ~30s (recompilation frontend) | **< 3s** |
| Raison | `reflex run` recompile le JS à chaque démarrage | Frontend pré-compilé, granian direct |

---

## 6. Architecture finale de déploiement

```
┌─────────────────────────────────────────────────┐
│                  Cloud Run                       │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │         Container (642 MB)               │    │
│  │                                          │    │
│  │  granian :8000 (ASGI)                    │    │
│  │    ├── WebSocket (Reflex state)          │    │
│  │    ├── API endpoints (/ping, ...)        │    │
│  │    └── Static files (.web/build/client)  │    │
│  │                                          │    │
│  │  terraform (CLI)  ──→ GCP Infra          │    │
│  │  infracost (CLI)  ──→ Cost estimation    │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Env vars :                                      │
│    __REFLEX_SKIP_COMPILE=true                    │
│    __REFLEX_MOUNT_FRONTEND_COMPILED_APP=true     │
│    REFLEX_BACKEND_ONLY=true                      │
│                                                  │
│  Secrets (Secret Manager v1) :                   │
│    SUPABASE_URL, SUPABASE_SERVICE_KEY,           │
│    INFRACOST_API_KEY                             │
└─────────────────────────────────────────────────┘
```

---

## 7. Arborescence finale du projet

```
EcoArch/
├── Dockerfile              ← Multi-stage optimisé (nouveau)
├── deploy.sh               ← Script de déploiement industrialisé (nouveau)
├── docker-compose.yml      ← Dev local (nettoyé)
├── .dockerignore            ← Restrictif avec exclusions sécurité (réécrit)
├── .env.example             ← Documentation complète des variables (réécrit)
├── requirements.txt         ← Nettoyé (-6 packages, +requests)
├── requirements-dev.txt     ← pytest, ruff, black, mypy
├── gcp-key.json             ← Clé service account (hors image Docker)
├── README.md
├── frontend/
│   ├── rxconfig.py          ← db_url supprimé (corrigé)
│   ├── requirements.txt     ← reflex==0.8.26 (pinné)
│   ├── assets/
│   └── frontend/
│       ├── __init__.py
│       ├── frontend.py      ← App Reflex principale
│       ├── state.py
│       ├── styles.py
│       └── components/
├── src/
│   ├── config.py            ← Secret Manager integration
│   ├── simulation.py        ← InfracostSimulator (utilise terraform + infracost CLI)
│   ├── parser.py
│   ├── recommendation.py
│   ├── budget_gate.py
│   ├── gitlab_comment.py
│   └── tasks.py             ← Celery workers
├── infra/                   ← Terraform configs (hors image Docker)
└── tests/                   ← 47 tests (hors image Docker)
    ├── test_parser.py
    ├── test_simulation.py
    └── test_state.py
```

**Fichiers supprimés** : `Dockerfile` (ancien), `Dockerfile.prod`, `deploy/`, `docker-compose.prod.yml`, `rapport_EcoArch.py`, `Rapport_EcoArch_V10.html`, `REFACTORING.md`, `gcp-key.json:Zone.Identifier`

---

## 8. Commandes de référence

### Déployer une nouvelle version
```bash
./deploy.sh                  # Auto-incrémente le patch
./deploy.sh v2.0.0           # Force une version
./deploy.sh --skip-build     # Redéploie sans rebuild
```

### Build local
```bash
docker build --build-arg VERSION=dev -t ecoarch-local .
docker run -p 8000:8000 --env-file .env ecoarch-local
```

### Rollback
```bash
gcloud run deploy ecoarch-app \
  --image gcr.io/ecoarch-mvp-1768828854/ecoarch-app:v1.1.0 \
  --region us-central1
```

### Dev local
```bash
docker compose up -d         # Lance ecoarch + redis
docker compose logs -f       # Voir les logs
```

### Tests
```bash
pip install -r requirements-dev.txt
pytest tests/ -v             # 47 tests
```
