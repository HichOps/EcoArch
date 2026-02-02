# EcoArch - Documentation du Refactoring

Ce document retrace l'évolution technique de la plateforme, passant d'un script monolithique à une architecture SaaS Intelligente et industrielle (V10).

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

## 🧠 Phase 4 : Intelligence & Expérience (Actuel - V10)
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

## 📊 État Final des Métriques

| Métrique | Début Projet | Version V10 (Finale) |
| :--- | :--- | :--- |
| **Approche** | Réactive (Calculatrice) | **Proactive (Conseiller)** |
| **Infrastructure** | VM Simple | **Cluster HA + Load Balancing** |
| **Gouvernance** | Aucune | **Budget Gate + Audit Trail Immuable** |
| **UX** | Monolithique | **Assistant vs Expert + Onglets** |
| **Installation** | Complexe (venv, deps...) | **1 Commande (Docker)** |