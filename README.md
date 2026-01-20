# 🌿 EcoArch: Plateforme de Gouvernance FinOps Automatisée

> **Shift-Left FinOps** : Estimez, contrôlez et optimisez les coûts Cloud avant même le déploiement.
Ce projet implémente un pipeline CI/CD intelligent sur GitLab qui calcule le coût de l'infrastructure Google Cloud (Terraform) lors de chaque Merge Request. Il bloque automatiquement les changements qui dépassent le budget défini, commente les analyses de coûts sur les MR, et alimente un Dashboard de suivi financier via Supabase.

---

## 📑 Sommaire Interactif

1. [🏗️ Architecture du Système](#architecture-du-système)
2. [🔄 Workflow FinOps (CI/CD)](#workflow-finops-cicd)
3. [🧠 Logique de la Budget Gate](#logique-de-la-budget-gate)
4. [📂 Structure du Projet](#structure-du-projet)
5. [🛠️ Stack Technique](#stack-technique)
6. [🚀 Installation & Configuration](#installation--configuration)
7. [📊 Base de Données & KPIs](#base-de-données--kpis)

---

## 🏗️ Architecture du Système

Le pipeline orchestre plusieurs outils pour transformer du code Terraform en indicateurs financiers exploitables.

```mermaid
graph TD
    %% Définition des styles
    classDef gitlab fill:#fca5a5,stroke:#b91c1c,stroke-width:2px,color:black;
    classDef terraform fill:#d8b4fe,stroke:#6b21a8,stroke-width:2px,color:black;
    classDef infracost fill:#fde047,stroke:#a16207,stroke-width:2px,color:black;
    classDef python fill:#86efac,stroke:#15803d,stroke-width:2px,color:black;
    classDef db fill:#93c5fd,stroke:#1e40af,stroke-width:2px,color:black;
    classDef dash fill:#ff9f43,stroke:#e67e22,stroke-width:2px,color:black;

    User([👤 Développeur]) -->|Push Code| GitLab(🦊 GitLab CI/CD)
    
    subgraph CI_Pipeline [Pipeline FinOps]
        GitLab --> TF[🏗️ Terraform Plan]
        TF -->|Analyse locale| IC[💰 Infracost Analysis]
        IC -->|Génère JSON| Report(📄 infracost-report.json)
        
        Report --> PyPars[🐍 Parser Python]
        PyPars --> PyGate[🚧 Budget Gate]
    end

    PyPars -->|Stockage Données| Supa[(🗄️ Supabase DB)]
    Supa --> Dash[📊 Dashboard App]
    PyGate -->|Commentaire MR| MR[💬 GitLab Merge Request]
    PyGate -->|Pass/Fail| Gate{🚦 Décision}

    class GitLab,MR gitlab;
    class TF terraform;
    class IC,Report infracost;
    class PyPars,PyGate python;
    class Supa db;
    class Dash dash;

```

---

## 🔄 Workflow FinOps (CI/CD)

Chaque modification de code déclenche une analyse en deux étapes : **Planification** (technique) et **Analyse** (financière).

```mermaid
sequenceDiagram
    autonumber
    participant Dev as 👤 Développeur
    participant CI as 🦊 CI Runner
    participant TF as 🏗️ Terraform
    participant IC as 💰 Infracost
    participant DB as 🗄️ Supabase

    Dev->>CI: Push Commit (Merge Request)
    
    rect rgb(240, 240, 255)
        note right of CI: Stage: PLAN
        CI->>TF: terraform plan (Validation technique)
    end

    rect rgb(235, 255, 235)
        note right of CI: Stage: FINOPS
        CI->>TF: terraform plan (Génération locale)
        CI->>IC: infracost breakdown --path tfplan.binary
        IC-->>CI: Estimation JSON
        
        CI->>CI: Script Parser.py (Calculs & KPIs)
        CI->>DB: INSERT INTO cost_history
        CI->>Dev: Commentaire automatique sur la MR
    end

    alt Coût < Budget (50$)
        CI->>Dev: ✅ Pipeline SUCCEEDED (Budget OK)
    else Coût > Budget (50$)
        CI->>Dev: ❌ Pipeline FAILED (Budget Exceeded)
    end

```

---

## 🧠 Logique de la "Budget Gate"

Le script `src/budget_gate.py` agit comme une barrière de sécurité financière.

```mermaid
flowchart TD
    %% Styles
    classDef start fill:#f3f4f6,stroke:#374151,stroke-width:2px;
    classDef logic fill:#c4b5fd,stroke:#5b21b6,stroke-width:2px;
    classDef pass fill:#86efac,stroke:#166534,stroke-width:2px;
    classDef fail fill:#fca5a5,stroke:#991b1b,stroke-width:2px;

    Start((🏁 Start)) --> ReadJSON[📖 Lecture Rapport]
    ReadJSON --> Extract[🔍 Extraction: total_monthly_cost]
    Extract --> Check{💸 Coût > $50 ?}
    
    Check -- OUI --> Alert[🚨 ALERTE ROUGE]
    %% CORRECTION ICI : Utilisation de guillemets et de <br/>
    Alert --> Fail["❌ Exit Code 1 <br/>(Bloque le Merge)"]
    
    Check -- NON --> Success[✅ ALERTE VERTE]
    %% CORRECTION ICI : Utilisation de guillemets et de <br/>
    Success --> Pass["✔️ Exit Code 0 <br/>(Autorise le Merge)"]

    class Start,ReadJSON,Extract start;
    class Check logic;
    class Success,Pass pass;
    class Alert,Fail fail;
```

---

## 📂 Structure du Projet

```bash
.
├── .gitlab-ci.yml      # Orchestration du Pipeline CI/CD
├── README.md           # Documentation du projet
├── dashboard/          # Interface de visualisation
│   └── app.py          # Application Dashboard (ex: Streamlit)
├── infra/              # Code Terraform (IaC)
│   ├── main.tf         # Ressources GCP (VM, Réseau...)
│   ├── variables.tf    # Définition des variables
│   ├── terraform.tfvars# Valeurs des variables (Environnement)
│   ├── outputs.tf      # Sorties Terraform
│   └── provider.tf     # Configuration Provider Google
├── src/                # Cœur de la logique FinOps (Python)
│   ├── budget_gate.py  # Bloque le pipeline si budget dépassé
│   ├── gitlab_comment.py # Bot qui commente les Merge Requests
│   ├── parser.py       # Transforme le JSON Infracost en KPI
│   └── utils/          # Fonctions utilitaires partagées
├── tests/              # Tests unitaires (Assurance Qualité)
│   └── test_parser.py  # Tests du parser JSON
└── requirements.txt    # Dépendances Python (Infracost, Supabase, etc.)

```

---

## 🛠️ Stack Technique

| Technologie | Rôle | Version |
| --- | --- | --- |
| **GitLab CI** | Orchestrateur du pipeline | SaaS |
| **Terraform** | Infrastructure as Code (GCP) | `1.10.0` |
| **Infracost** | Moteur de calcul des coûts Cloud | `v0.10.43` |
| **Python** | Parsing, Logique métier, API GitLab | `3.11` |
| **Supabase** | Base de données (Historique & Dashboard) | PostgreSQL |

---

## 🚀 Installation & Configuration

### 1. Variables CI/CD (GitLab)

Pour que le pipeline fonctionne, les variables suivantes doivent être définies dans **Settings > CI/CD > Variables** :

* `GCP_ID_TOKEN` : Configuration OIDC (Gérée par le template d'auth).
* `INFRACOST_API_KEY` : Clé API Infracost (Gratuite).
* `SUPABASE_URL` : URL de votre projet Supabase.
* `SUPABASE_SERVICE_KEY` : Clé secrète (`service_role`) pour l'écriture en DB.
* `GL_TOKEN` : Token d'accès GitLab (Project Access Token) pour commenter sur les MR.
* `ECOARCH_BUDGET_LIMIT` : Seuil budgétaire (ex: `50.00`).
* `TF_STATE_BUCKET` : Bucket GCS pour le state Terraform.
* `TF_STATE_PREFIX` : Préfixe du state (ex: `terraform/state`).

---

## 📊 Base de Données & KPIs

Les données collectées permettent de générer des vues SQL pour le suivi FinOps.

### Création de la Table

Dans le **SQL Editor** de Supabase :

```sql
CREATE TABLE cost_history (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    project_id TEXT,
    branch_name TEXT,
    commit_sha TEXT,
    author TEXT,
    total_monthly_cost NUMERIC,
    diff_monthly_cost NUMERIC,
    currency TEXT,
    budget_limit NUMERIC,
    status TEXT
);

```

### Vue d'Optimisation (Money Saved)

Cette vue calcule combien chaque commit a fait économiser (ou dépenser) par rapport au précédent.

```sql
CREATE VIEW vw_finops_optimization AS
SELECT 
    commit_sha,
    author,
    created_at,
    total_monthly_cost as new_cost,
    LAG(total_monthly_cost) OVER (ORDER BY created_at) as previous_cost,
    LAG(total_monthly_cost) OVER (ORDER BY created_at) - total_monthly_cost as money_saved
FROM cost_history
WHERE branch_name = 'main' OR branch_name = 'feat/finops-bot-test'
ORDER BY created_at DESC;

```

---

*Projet réalisé dans le cadre de la mise en place d'une gouvernance FinOps automatisée.*
