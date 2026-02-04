# EcoArch - Documentation du Refactoring

Ce document retrace l'évolution technique de la plateforme, passant d'un script monolithique à une architecture SaaS Intelligente et industrielle (V11).

---

## 🔄 Phase 1 : Modularisation du Backend (Python)
* **Objectif** : Clean Architecture & Testabilité.
* **Avant** : Code spaghetti dans un seul fichier `app.py`.
* **Après** : 
    * Séparation en modules `src/config.py` (Configuration) et `src/simulation.py` (Moteur Terraform).
    * Isolation des appels systèmes (Infracost/Terraform CLI).
    * Ajout de tests unitaires.

---

## ✨ Phase 2 : Modernisation du Frontend (Reflex)
* **Objectif** : Performance & UX Réactive.
* **Avant** : Streamlit (rechargement de page constant, UX limitée).
* **Après** : 
    * Framework **Reflex** (React wrapper).
    * Gestion d'état (State) temps réel.
    * WebSockets pour le streaming de logs Terraform.
    * Design System (Glassmorphism, Néon).

---

## 🐳 Phase 3 : Industrialisation (Docker & Terraform)
* **Objectif** : Robustesse, Cycle de Vie & Multi-Tenant.
* **Réalisations** : 
    * **Conteneurisation** : `Dockerfile` multi-stage et `docker-compose` pour l'orchestration.
    * **Cycle de Vie** : Implémentation du `terraform destroy` et de la récupération de session.
    * **Isolation du State** : Chaque session utilisateur génère un UUID unique. Les fichiers `tfstate` sont isolés dans des dossiers GCS distincts (`terraform/state/{uuid}/`), empêchant les conflits entre utilisateurs (Alice vs Bob).

---

## 🧠 Phase 4 : Intelligence & Expérience (V10)
* **Objectif** : Transformer l'outil en "Assistant Architecte" (Day 0).

### 1. Moteur de Recommandation (`src/recommendation.py`)
Création d'un moteur de règles métier capable de traduire des intentions floues en spécifications techniques précises.
* **Haute Disponibilité (HA)** : Détection automatique des besoins critiques. Génération de clusters (2 VMs) et ajout de **Load Balancers** globaux.
* **Profilage de Charge** : Sélection intelligente des instances (`highcpu` vs `highmem`) selon la nature de la charge de travail.

### 2. Assistant UX (Wizard)
* Introduction du **"Mode Assistant"** (IA symbolique) en alternative au mode Expert.
* Logique d'**Auto-Déploiement** : Provisionning automatique si le budget estimé respecte les seuils de gouvernance.

### 3. Visibilité & Audit
* **Top Bar Persistante** : Gestion de l'identité et de la session visible en permanence.
* **Data Grid d'Audit** : Intégration d'un tableau de logs interactif connecté à Supabase. Permet aux équipes FinOps de visualiser l'historique des actions (Qui/Quoi/Combien) sans accès direct à la base de données.

---

## 🍎 Phase 5 : UX Apple-like & Optimisations (Actuel - V11)
* **Objectif** : Design épuré, stabilité et flexibilité accrue.

### 1. Refonte Design System
* **Style Apple** : Interface minimaliste avec palette de couleurs cohérente (bleu #007AFF, vert #34C759, etc.).
* **Thème Clair/Sombre** : Support natif du mode sombre avec variables CSS adaptatives.
* **Animations** : Transitions fluides (fade-in, scale) et effets glass morphism subtils.
* **Typographie** : Polices système SF Pro avec espacement optimisé (-0.02em).

### 2. Console de Déploiement Améliorée
* **Persistance** : La console reste visible après le déploiement (statut SUCCESS/ERROR).
* **Indicateurs visuels** : Spinner pendant l'exécution, icônes de statut dynamiques.
* **Fermeture manuelle** : Bouton "X" pour fermer la console quand souhaité.
* **Style Terminal macOS** : Traffic lights (rouge/jaune/vert) et fond sombre.

### 3. Mode Économie (Sans Base de Données)
* **Option flexible** : Checkbox "Inclure une base de données" dans le wizard.
* **Économies** : Permet de passer de ~$23/mois à ~$7/mois en excluant Cloud SQL.
* **Cas d'usage** : Idéal pour les tests, démos ou environnements sans besoin de persistance.

### 4. Corrections Techniques
* **Terraform HCL** : Utilisation de heredoc (`<<-EOF`) pour les scripts multi-lignes (startup-script).
* **Simulation Infracost** : Génération de Terraform sans backend GCS pour les estimations.
* **Compatibilité API** : Documentation des APIs GCP requises (Compute, Storage) vs optionnelles (SQL).

---

## 📊 État Final des Métriques

| Métrique | Début Projet | Version V11 (Actuelle) |
| :--- | :--- | :--- |
| **Approche** | Réactive (Calculatrice) | **Proactive (Conseiller)** |
| **Infrastructure** | VM Simple | **Cluster HA + Load Balancing** |
| **Gouvernance** | Aucune | **Budget Gate + Audit Trail Immuable** |
| **UX** | Monolithique | **Assistant vs Expert + Onglets** |
| **Design** | Basique | **Apple-like (Light/Dark)** |
| **Flexibilité** | Tout ou Rien | **Options modulaires (avec/sans DB)** |
| **Installation** | Complexe (venv, deps...) | **1 Commande (Docker)** |

---

## 🛣️ Roadmap Future

| Fonctionnalité | Priorité | Statut |
| :--- | :--- | :--- |
| Support multi-cloud (AWS/Azure) | Moyenne | 📋 Planifié |
| Recommandations ML (coûts historiques) | Basse | 💡 Idée |
| Export PDF des rapports d'audit | Moyenne | 📋 Planifié |
| Notifications Slack/Teams | Basse | 💡 Idée |