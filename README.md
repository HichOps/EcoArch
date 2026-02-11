# 🌿 EcoArch — Plateforme FinOps Intelligente

> **From Zero to Hero** : Concevez, estimez, déployez et auditez vos infrastructures GCP — le tout depuis une interface unique.

**EcoArch** est une plateforme FinOps « Day 0 → Day 2 » qui combine un architecte virtuel (Wizard IA), un mode Expert granulaire, un pipeline GitLab CI/CD complet (Terraform + Infracost), et une traçabilité d'audit temps réel.

![Version](https://img.shields.io/badge/Version-v0.0.18-blue)
![Pipeline](https://img.shields.io/badge/CI%2FCD-GitLab_4%2F4_jobs-green)
![Tests](https://img.shields.io/badge/Tests-195_passed-brightgreen)
![Stack](https://img.shields.io/badge/Stack-Reflex_%7C_Terraform_%7C_Infracost-purple)
![Deploy](https://img.shields.io/badge/Deploy-Cloud_Run-orange)
![License](https://img.shields.io/badge/License-MIT-gray)

---

## 📑 Table des matières

1. [Architecture Globale](#-architecture-globale)
2. [Arborescence du Projet](#-arborescence-du-projet)
3. [Pipeline CI/CD](#-pipeline-cicd)
4. [Flux de Déploiement](#-flux-de-déploiement)
5. [Terraform Dynamique](#-terraform-dynamique)
6. [Software Stacks (Startup Scripts)](#-software-stacks-startup-scripts)
7. [Audit & Status Polling](#-audit--status-polling)
8. [Fonctionnalités Clés](#-fonctionnalités-clés)
9. [Installation & Configuration](#-installation--configuration)
10. [Guide Utilisateur](#-guide-utilisateur)
11. [Tests](#-tests)
12. [Secrets & Sécurité](#-secrets--sécurité)
13. [APIs GCP Requises](#-apis-gcp-requises)

---

## 🏗️ Architecture Globale

```mermaid
graph TB
    subgraph CLIENT["🖥️ Navigateur"]
        UI["Interface Reflex<br/><i>Apple-style Design</i>"]
    end

    subgraph CLOUDRUN["☁️ Cloud Run"]
        direction TB
        FE["Frontend Reflex<br/><i>(SSR + WebSocket)</i>"]
        BE["Backend Python<br/><i>State Manager</i>"]
        FE <--> BE
    end

    subgraph GITLAB["🦊 GitLab CI/CD"]
        direction TB
        PLAN["terraform_plan"]
        TEST["unit_tests<br/>static_analysis"]
        FINOPS["infracost_analysis<br/>budget_gate"]
        DEPLOY["terraform_deploy<br/><i>(Trigger API)</i>"]
    end

    subgraph GCP["☁️ Google Cloud Platform"]
        direction TB
        VM["🖥️ Compute Engine<br/><i>VMs + startup_script</i>"]
        SQL["🗄️ Cloud SQL<br/><i>PostgreSQL</i>"]
        GCS["📦 Cloud Storage<br/><i>Buckets</i>"]
        SM["🔑 Secret Manager"]
    end

    subgraph DATA["💾 Données"]
        SUPA[("Supabase<br/><i>profiles + audit_logs</i>")]
        TFSTATE[("GitLab HTTP Backend<br/><i>Terraform State</i>")]
    end

    UI -- "HTTPS" --> FE
    BE -- "POST trigger/pipeline" --> GITLAB
    BE -- "GET pipelines/:id<br/><i>(status polling)</i>" --> GITLAB
    DEPLOY -- "terraform apply" --> GCP
    BE -- "read/write" --> SUPA
    BE -- "get secrets" --> SM
    GITLAB -- "state lock/unlock" --> TFSTATE
    PLAN --> TEST --> FINOPS

    style CLIENT fill:#1a1a2e,stroke:#e94560,color:#eee
    style CLOUDRUN fill:#0f3460,stroke:#e94560,color:#eee
    style GITLAB fill:#292929,stroke:#fc6d26,color:#eee
    style GCP fill:#1a3a5c,stroke:#4285f4,color:#eee
    style DATA fill:#1e1e2e,stroke:#a855f7,color:#eee
```

---

## 📂 Arborescence du Projet

```
EcoArch/
├── .gitlab-ci.yml          # Pipeline CI/CD (4 stages, 4 jobs)
├── Dockerfile              # Build multi-stage (Python 3.11 + Terraform + Infracost)
├── deploy.sh               # Script de déploiement Cloud Run (auto-versioning)
├── docker-compose.yml      # Stack développement local
├── requirements.txt        # Dépendances Python (production)
├── requirements-dev.txt    # Dépendances dev (pytest, ruff, mypy)
├── .env.example            # Template des variables d'environnement
│
├── frontend/               # Application Reflex
│   ├── rxconfig.py         # Configuration Reflex (app_name, api_url)
│   └── frontend/
│       ├── frontend.py     # Routes & layout principal
│       ├── state.py        # État global (840+ lignes) — cœur de l'app
│       ├── styles.py       # Thème Apple-style + couleurs recharts
│       └── components/
│           ├── topbar.py   # Barre d'identité utilisateur
│           ├── header.py   # En-tête avec logo & mode switch
│           ├── wizard.py   # Questionnaire IA (5 questions)
│           ├── form.py     # Formulaire mode Expert
│           ├── cards.py    # Cartes de résumé (coût, budget, ressources)
│           ├── resources.py# Liste du panier
│           ├── pricing.py  # Graphique donut recharts (coûts par ressource)
│           ├── stats.py    # Statistiques de session
│           ├── logs.py     # Console de déploiement temps réel
│           └── audit_view.py # Tableau d'audit (Data Grid)
│
├── src/                    # Logique métier
│   ├── config.py           # Configuration centralisée + GCPConfig (SOFTWARE_STACKS)
│   ├── simulation.py       # Simulateur Infracost (estimation des coûts)
│   ├── recommendation.py   # Moteur de recommandation IA (Wizard → architecture)
│   ├── deployer.py         # Trigger GitLab CI/CD + polling statut pipeline
│   ├── parser.py           # Parser du rapport Infracost JSON
│   ├── budget_gate.py      # Gate budgétaire (seuil configurable)
│   ├── gitlab_comment.py   # Commentaire MR automatique (rapport coûts)
│   └── stubs.py            # Stubs pour dev frontend sans backend
│
├── infra/                  # Infrastructure as Code
│   ├── main.tf             # Ressources dynamiques (VM, SQL, GCS via jsondecode)
│   ├── variables.tf        # Variables Terraform (architecture_json, deployment_id…)
│   ├── providers.tf        # Provider Google ~> 6.15.0
│   └── outputs.tf          # Outputs (IPs, noms, deployment_id)
│
├── tests/                  # Suite de tests (195 tests)
│   ├── test_deployer.py    # Tests trigger + enrichissement + polling (38 tests)
│   ├── test_simulation.py  # Tests simulateur Infracost
│   ├── test_parser.py      # Tests parser rapport
│   ├── test_recommendation.py # Tests moteur de recommandation
│   └── test_state.py       # Tests état Reflex (login, panier, audit)
│
├── AUDIT_SECURITE_QUALITE.md  # Rapport d'audit sécurité & qualité
└── RAPPORT_DEPLOIEMENT.md     # Historique de déploiement & troubleshooting
```

---

## 🔄 Pipeline CI/CD

Le pipeline GitLab s'exécute en **4 stages** selon la source de déclenchement :

```mermaid
graph LR
    subgraph PUSH["📦 Sur push / MR"]
        direction LR
        P1["🔧 plan<br/><b>terraform_plan</b>"]
        P2a["🧪 test<br/><b>unit_tests</b>"]
        P2b["🔍 test<br/><b>static_analysis</b>"]
        P3["💰 finops<br/><b>infracost_analysis</b><br/>+ budget_gate"]
        P1 --> P2a & P2b --> P3
    end

    subgraph TRIGGER["🚀 Sur trigger API"]
        direction LR
        T1["🏗️ deploy<br/><b>terraform_deploy</b><br/><i>apply / destroy</i>"]
    end

    style PUSH fill:#0d1117,stroke:#58a6ff,color:#eee
    style TRIGGER fill:#0d1117,stroke:#f97316,color:#eee
    style P1 fill:#238636,stroke:#238636,color:#fff
    style P2a fill:#238636,stroke:#238636,color:#fff
    style P2b fill:#238636,stroke:#238636,color:#fff
    style P3 fill:#238636,stroke:#238636,color:#fff
    style T1 fill:#da3633,stroke:#da3633,color:#fff
```

| Stage | Job | Déclencheur | Description |
|-------|-----|-------------|-------------|
| `plan` | `terraform_plan` | push / MR | `terraform init` + `plan` → artifact `plan.json` |
| `test` | `unit_tests` | push / MR | `pytest` — 195 tests, rapport JUnit |
| `test` | `static_analysis` | push / MR | `mypy` + `ruff` (allow_failure) |
| `finops` | `infracost_analysis` | push / MR | Infracost breakdown + `budget_gate.py` (seuil 50$) |
| `deploy` | `terraform_deploy` | trigger / web | `terraform apply` ou `destroy` selon `ECOARCH_ACTION` |

**Authentification GCP** : Workload Identity Federation (pas de clé JSON en CI).

---

## 🚀 Flux de Déploiement

Voici le parcours complet d'un déploiement déclenché depuis l'interface :

```mermaid
sequenceDiagram
    actor User as 👤 Utilisateur
    participant App as 🖥️ EcoArch<br/>(Cloud Run)
    participant Supa as 💾 Supabase
    participant GL as 🦊 GitLab API
    participant TF as 🏗️ Terraform<br/>(CI Runner)
    participant GCP as ☁️ GCP

    User->>App: Clic "DÉPLOYER"
    activate App
    App->>Supa: INSERT audit_log (status: PENDING)
    App->>App: Enrichit les ressources<br/>(startup_script injecté)
    App->>GL: POST /trigger/pipeline<br/>{architecture_json, deployment_id, action}
    GL-->>App: 201 {pipeline_id, web_url}
    App->>Supa: UPDATE audit_log → PIPELINE_SENT
    App-->>User: 🔗 Lien pipeline affiché
    deactivate App

    GL->>TF: Démarre terraform_deploy
    activate TF
    TF->>TF: terraform init (HTTP backend)
    TF->>TF: terraform plan → apply
    TF->>GCP: Crée VM + SQL + GCS
    GCP-->>TF: Ressources créées ✅
    TF-->>GL: Job SUCCESS
    deactivate TF

    User->>App: Clic "🔄 Actualiser" (audit)
    activate App
    App->>GL: GET /pipelines/{id} (status?)
    GL-->>App: {status: "success"}
    App->>Supa: UPDATE audit_log → SUCCESS
    App-->>User: ✅ Statut mis à jour
    deactivate App
```

---

## 🧱 Terraform Dynamique

Le fichier `main.tf` ne contient plus de ressource statique. Il décode le JSON du panier utilisateur et crée dynamiquement chaque ressource :

```mermaid
graph TD
    JSON["📋 architecture_json<br/><i>(envoyé par l'app)</i>"]
    DECODE["jsondecode()"]
    FILTER["Filtrage par type"]

    VM["🖥️ google_compute_instance.vm<br/><i>count = N compute</i><br/>+ metadata_startup_script"]
    SQL["🗄️ google_sql_database_instance.db<br/><i>count = N sql</i>"]
    GCS["📦 google_storage_bucket.bucket<br/><i>count = N storage</i>"]

    JSON --> DECODE --> FILTER
    FILTER -->|type == compute| VM
    FILTER -->|type == sql| SQL
    FILTER -->|type == storage| GCS

    style JSON fill:#1e293b,stroke:#60a5fa,color:#eee
    style DECODE fill:#1e293b,stroke:#a78bfa,color:#eee
    style FILTER fill:#1e293b,stroke:#f59e0b,color:#eee
    style VM fill:#065f46,stroke:#34d399,color:#eee
    style SQL fill:#581c87,stroke:#c084fc,color:#eee
    style GCS fill:#7c2d12,stroke:#fb923c,color:#eee
```

**Variables Terraform** (toutes injectées par le pipeline) :

| Variable | Source | Description |
|----------|--------|-------------|
| `architecture_json` | `TF_VAR_architecture_json` | JSON du panier (ressources + startup_script) |
| `deployment_id` | `TF_VAR_deployment_id` | ID unique de session (UUID court) |
| `project_id` | `TF_VAR_project_id` | Projet GCP cible |
| `region` / `zone` | Variables globales CI | `us-central1` / `us-central1-a` |

---

## 📦 Software Stacks (Startup Scripts)

Chaque VM peut être provisionnée avec un logiciel pré-installé via `metadata_startup_script`. Le script est injecté dans le JSON par `deployer.py` depuis `GCPConfig.SOFTWARE_STACKS` :

| Stack ID | Nom | Logiciels installés |
|----------|-----|---------------------|
| `none` | VM vide | — |
| `web-nginx` | Serveur Web (Nginx) | Nginx + Certbot HTTPS |
| `web-apache` | Serveur Web (Apache) | Apache2 + mod_ssl |
| `nodejs` | Node.js Runtime | Node.js 20 LTS + npm + PM2 |
| `python-django` | Python Django | Python 3.11 + Django + Gunicorn + Nginx |
| `python-flask` | Python Flask | Python 3.11 + Flask + Gunicorn |
| `docker` | Docker | Docker Engine + Docker Compose |
| `lamp` | LAMP Stack | Apache + MySQL + PHP |
| `lemp` | LEMP Stack | Nginx + MySQL + PHP-FPM |
| `monitoring` | Monitoring | Prometheus + Node Exporter + Grafana |

```mermaid
graph LR
    CART["🛒 Panier<br/><i>software_stack: docker</i>"]
    ENRICH["deployer.py<br/><b>enrich_resources</b>"]
    GCPCONF["GCPConfig<br/>.SOFTWARE_STACKS"]
    TF["Terraform<br/><b>metadata_startup_script</b>"]
    VM["🖥️ VM GCP<br/><i>Docker installé au boot</i>"]

    CART --> ENRICH
    GCPCONF -.->|get_startup_script| ENRICH
    ENRICH -->|JSON enrichi| TF --> VM

    style CART fill:#1e293b,stroke:#60a5fa,color:#eee
    style ENRICH fill:#1e293b,stroke:#a78bfa,color:#eee
    style GCPCONF fill:#1e293b,stroke:#f59e0b,color:#eee
    style TF fill:#1e293b,stroke:#34d399,color:#eee
    style VM fill:#065f46,stroke:#34d399,color:#eee
```


## 📊 Audit & Status Polling

Le système d'audit trace chaque action (deploy/destroy) dans Supabase. Le statut est mis à jour en interrogeant l'API GitLab :

```mermaid
stateDiagram-v2
    [*] --> PENDING: Création audit_log
    PENDING --> PIPELINE_SENT: GitLab trigger OK
    PIPELINE_SENT --> SUCCESS: Pipeline terminé ✅
    PIPELINE_SENT --> FAILED: Pipeline échoué ❌
    PIPELINE_SENT --> CANCELLED: Pipeline annulé 🚫
    PIPELINE_SENT --> RUNNING: Pipeline en cours ⏳
    RUNNING --> SUCCESS: Terminé
    RUNNING --> FAILED: Terminé

    PENDING --> PENDING: GitLab indisponible<br/>(aucun polling)
```

**Colonnes `audit_logs`** (Supabase) :

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | int | Clé primaire auto |
| `user` | text | Utilisateur ayant déclenché l'action |
| `action` | text | `DEPLOY` ou `DESTROY` |
| `resources_summary` | text | Résumé du panier (ex: `[abc123] VM e2-medium (Docker), GCS STANDARD`) |
| `total_cost` | float | Coût mensuel estimé |
| `status` | text | `PENDING` → `PIPELINE_SENT` → `SUCCESS` / `FAILED` / `CANCELLED` |
| `pipeline_url` | text | Lien cliquable vers le pipeline GitLab |
| `created_at` | timestamp | Date de création |

---

## ✨ Fonctionnalités Clés

| Fonctionnalité | Description |
|----------------|-------------|
| 🧠 **Wizard IA** | Questionnaire (5 questions) → architecture optimisée automatiquement |
| 🛠️ **Mode Expert** | Sélection manuelle des VMs, Cloud SQL, Cloud Storage, software stack |
| 💰 **Estimation temps réel** | Calcul Infracost avant déploiement (graphique donut interactif) |
| 🚀 **Déploiement GitLab** | Trigger API → pipeline Terraform → VMs créées avec logiciels pré-installés |
| 🔥 **Destruction** | Trigger API → `terraform destroy` → nettoyage complet |
| 📊 **Audit immuable** | Tableau Supabase avec polling GitLab (PENDING → SUCCESS/FAILED) |
| 🔒 **Budget Gate** | Seuil configurable (défaut: 50$) — bloque le déploiement si dépassé |
| 👤 **Multi-tenant** | Chaque session = ID unique, Terraform state isolé |
| 🎨 **Design Apple-style** | Thème clair/sombre, glass morphism, animations fluides |

---

## 🚀 Installation & Configuration

### Prérequis

- **Python 3.11+**
- **Docker** (pour le build Cloud Run ou le dev local)
- **Compte GCP** avec projet configuré
- **Compte GitLab** avec CI/CD activé
- **Compte Supabase** (table `profiles` + `audit_logs`)

### Développement local

```bash
# 1. Cloner le projet
git clone git@gitlab.com:HichOps/ecoarch.git
cd EcoArch

# 2. Environnement virtuel
python3 -m venv venv && source venv/bin/activate

# 3. Dépendances
pip install -r requirements.txt -r requirements-dev.txt
pip install -r frontend/requirements.txt

# 4. Configuration
cp .env.example .env
# → Remplir les clés : SUPABASE_URL, SUPABASE_SERVICE_KEY, INFRACOST_API_KEY,
#   GITLAB_TRIGGER_TOKEN, GITLAB_API_TOKEN

# 5. Lancer l'app
cd frontend && reflex run
```

Accès : **http://localhost:3000**

### Développement avec Docker

```bash
docker compose up --build
```

### Déploiement Cloud Run (production)

```bash
# Le script gère : auto-versioning, tests, Docker build, Cloud Run deploy
bash deploy.sh patch   # patch | minor | major
```

---

## 🛠️ Guide Utilisateur

### 1. Connexion

Saisissez votre identifiant dans la Top Bar. Le profil est vérifié dans Supabase (`profiles`).

### 2. Conception

- **Mode Assistant (Wizard)** : Répondez aux 5 questions métier → l'IA génère l'architecture.
- **Mode Expert** : Ajoutez manuellement chaque ressource (VM, SQL, Storage) avec la stack logicielle.

### 3. Estimation

Le coût s'affiche en temps réel dans le graphique donut. Chaque ressource a sa propre couleur par type.

### 4. Déploiement

Cliquez sur **DÉPLOYER** → le pipeline GitLab est déclenché. Suivez le lien dans la console de logs.

### 5. Audit

Cliquez sur **🔄 Actualiser** dans l'onglet Audit → les statuts PENDING/PIPELINE_SENT sont interrogés auprès de GitLab et mis à jour automatiquement.

### 6. Destruction

Cliquez sur **DÉTRUIRE L'INFRA** ou saisissez un Deployment ID précédent.

---

## 🧪 Tests

```bash
# Lancer tous les tests (195)
python -m pytest tests/ -v

# Avec couverture
python -m pytest tests/ --cov=src --cov-report=term-missing

# Un fichier spécifique
python -m pytest tests/test_deployer.py -v
```

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `test_deployer.py` | 38 | trigger, enrichissement, polling, extraction |
| `test_simulation.py` | 52 | fallback, Infracost mock, edge cases |
| `test_parser.py` | 33 | parsing rapport JSON |
| `test_recommendation.py` | 38 | moteur IA, tous les scénarios |
| `test_state.py` | 34 | login, panier, audit, wizard |

---

## 🔐 Secrets & Sécurité

Tous les secrets sensibles sont stockés dans **GCP Secret Manager** en production. En dev local, ils sont lus depuis le `.env`.

| Secret | Usage | Scope |
|--------|-------|-------|
| `SUPABASE_URL` | URL Supabase | — |
| `SUPABASE_SERVICE_KEY` | Clé service Supabase | write |
| `infracost-api-key` | Clé API Infracost | — |
| `GITLAB_TRIGGER_TOKEN` | Token trigger pipeline | trigger |
| `GITLAB_API_TOKEN` | Token lecture statut pipeline | `read_api` |

**Bonnes pratiques appliquées** :
- ❌ Aucune clé JSON GCP dans le repo (Workload Identity Federation en CI)
- ✅ `.gitignore` exclut `*.tfvars`, `.env`, `gcp-key.json*`
- ✅ Authentification HMAC optionnelle (`AUTH_SECRET_KEY`)
- ✅ Terraform state dans GitLab HTTP Backend (pas de bucket public)

---

## ☁️ APIs GCP Requises

| API | Obligatoire | Usage |
|-----|:-----------:|-------|
| Compute Engine API | ✅ | Création de VMs |
| Cloud Storage API | ✅ | Buckets de stockage |
| Cloud SQL Admin API | ⚠️ Optionnel | Bases de données (désactivable dans le Wizard) |
| Secret Manager API | ✅ | Lecture des secrets en production |
| Cloud Run Admin API | ✅ | Déploiement de l'application |
| Artifact Registry API | ✅ | Stockage des images Docker |
| IAM Service Account Credentials API | ✅ | Workload Identity Federation (CI/CD) |

---

<p align="center">
  <b>EcoArch v0.0.18</b> — Built with 🌿 by <a href="https://gitlab.com/HichOps">HichOps</a>
</p>

