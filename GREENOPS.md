# 🌍 GREENOPS.md — Manifeste Méthodologique GreenOps

> **EcoArch** intègre une approche scientifique de mesure et d'optimisation de l'empreinte carbone des infrastructures cloud GCP.
> Ce document détaille les facteurs d'émission, les modèles de calcul et la méthodologie de scoring.

---

## 1. Philosophie : Green by Design

Chaque architecture générée par EcoArch est **sobre par défaut**. Le système applique trois principes :

1. **Smallest Viable Resource** — Toujours recommander le plus petit type de machine compatible (famille E2 en priorité).
2. **Low-Carbon Region First** — Avertir l'utilisateur si la région choisie est à forte intensité carbone et proposer une alternative.
3. **Storage Sobriety** — Défaut sur `pd-standard` (HDD) plutôt que `pd-ssd`, sauf demande explicite ou workload I/O-intensif.

---

## 2. Facteurs d'Émission

### 2.1 Intensité Carbone Régionale (gCO2eq/kWh)

Les régions GCP sont classées en 3 catégories selon leur mix énergétique :

| Catégorie | gCO2eq/kWh | Régions GCP | Source |
| :--- | :---: | :--- | :--- |
| **Low** | 50 | `europe-west1` (Belgique), `europe-north1` (Finlande), `europe-west9` (Paris), `northamerica-northeast1` (Montréal), `canada-central1` | Google Cloud Carbon Footprint |
| **Medium** | 380 | `europe-west4` (Pays-Bas), `us-central1` (Iowa) | Cloud Carbon Footprint |
| **High** | 700 | `europe-central2` (Varsovie), `us-east4` (Virginie) | Cloud Carbon Footprint |

> **Source** : [Google Cloud Region Picker](https://cloud.google.com/sustainability/region-carbon), [Cloud Carbon Footprint](https://www.cloudcarbonfootprint.org/)

### 2.2 Consommation Électrique des Instances (kWh/mois)

Basé sur les benchmarks de **Teads Engineering** et **Cloud Carbon Footprint** :

| Famille | Type d'Instance | vCPU | RAM (GB) | kWh/mois | Note GreenOps |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **E2** (shared-core) | `e2-micro` | 0.25 | 1 | 5.0 | Très sobre |
| | `e2-small` | 0.5 | 2 | 8.0 | Sobre |
| | `e2-medium` | 1 | 4 | 15.0 | Standard |
| | `e2-standard-2` | 2 | 8 | 25.0 | Correct |
| | `e2-standard-4` | 4 | 16 | 35.0 | Modéré |
| | `e2-highcpu-2` | 2 | 2 | 15.0 | CPU-optimisé |
| | `e2-highmem-2` | 2 | 16 | 18.0 | Mémoire-optimisé |
| **N1** (dedicated) | `n1-standard-1` | 1 | 3.75 | 22.0 | Plus consommateur |
| **N2** (dedicated) | `n2-standard-2` | 2 | 8 | 30.0 | Élevé |
| | `n2-standard-4` | 4 | 16 | 45.0 | Élevé |
| **C2** (compute-optimized) | `c2-standard-4` | 4 | 16 | 45.0 | Très élevé |

> La famille E2 utilise des vCPUs partagés (shared-core) : en idle, la consommation tend vers 0W. Les familles N1/N2/C2 utilisent des cores dédiés, avec une consommation plancher même au repos.

### 2.3 Consommation Stockage (kWh/mois/TB)

| Type de Disque | kWh/mois/TB | Technologie | Usage recommandé |
| :--- | :---: | :--- | :--- |
| `pd-standard` (HDD) | 0.65 | Disque magnétique | Données froides, logs, backups |
| `pd-balanced` | ~0.80 | Hybride | Usage général |
| `pd-ssd` (SSD) | 1.20 | Flash NAND | BDD transactionnelles, I/O intensif |

> **Source** : Estimations basées sur les benchmarks de consommation des disques entreprise (Western Digital, Seagate). Le ratio SSD/HDD est d'environ 1.85x en énergie pour la même capacité.

---

## 3. Modèle de Calcul des Émissions

### 3.1 Formule Principale

```
kgCO2eq/mois = (kWh_compute + kWh_stockage) × gCO2eq_par_kWh / 1000
```

Où :
- `kWh_compute` = somme des consommations de chaque instance (voir table 2.2)
- `kWh_stockage` = `disk_size_GB / 1000 × kWh_par_TB` (voir table 2.3)
- `gCO2eq_par_kWh` = intensité carbone de la région sélectionnée (voir table 2.1)

### 3.2 Exemple Concret

| Ressource | Calcul | kWh/mois |
| :--- | :--- | :---: |
| 1× `e2-medium` | 15.0 | 15.0 |
| Boot disk 50 GB `pd-standard` | 50 / 1000 × 0.65 | 0.033 |
| **Total** | | **15.033** |

Pour la région `us-central1` (medium, 380 gCO2eq/kWh) :

```
kgCO2eq = 15.033 × 380 / 1000 = 5.71 kgCO2eq/mois
```

---

## 4. Green Score (Sobriety Score A → E)

Le Green Score est un indicateur qualitatif calculé en 4 étapes :

### 4.1 Pipeline de Calcul

```
Hardware Impact → Environmental Modifier → Regional Factor → Letter Grade
```

### 4.2 Étape 1 : Hardware Impact (score brut)

| Critère | Condition | Points |
| :--- | :--- | :---: |
| **vCPU** | ≤ 2 | 0 |
| | ≤ 4 | +1 |
| | ≤ 8 | +2 |
| | > 8 | +3 |
| **RAM** | ≤ 8 GB | 0 |
| | ≤ 32 GB | +1 |
| | > 32 GB | +2 |
| **Storage** | `MULTI_REGIONAL` bucket | +1 par bucket |

### 4.3 Étape 2 : Environmental Modifier

| Environnement | Modificateur |
| :--- | :--- |
| `dev` | score - 1 (minimum 0) |
| `prod` | Aucun changement |

> Justification : un environnement de développement tourne moins longtemps et sert moins de trafic.

### 4.4 Étape 3 : Regional Factor (multiplicateur)

| Catégorie Région | Facteur |
| :--- | :---: |
| Low (Europe Nord/Ouest, Canada) | × 0.8 |
| Medium (US Central, NL) | × 1.0 |
| High (Pologne, Virginie) | × 1.2 |

### 4.5 Étape 4 : Letter Grade

| Score Final | Note | Interprétation |
| :---: | :---: | :--- |
| ≤ 1.0 | **A** | Très sobre |
| ≤ 2.0 | **B** | Sobre |
| ≤ 3.0 | **C** | Modéré |
| ≤ 4.0 | **D** | Gourmand |
| > 4.0 | **E** | Très gourmand |

---

## 5. Équivalence Carbone : km en Voiture Thermique

Pour contextualiser les émissions, EcoArch affiche une équivalence en kilomètres parcourus :

```
km_equivalent = kgCO2eq × 5.0
```

| Source | Valeur | Référence |
| :--- | :--- | :--- |
| Émission moyenne voiture thermique (France) | ~200 gCO2/km | ADEME |
| Facteur de conversion | 1 kgCO2eq ≈ 5 km | Arrondi ADEME |

**Exemple** : 5.71 kgCO2eq/mois ≈ 28 km en voiture thermique par mois.

---

## 6. Guardrails Automatiques

| Guardrail | Déclencheur | Action |
| :--- | :--- | :--- |
| **Sobriety Alert** | Score ≥ C | Suggestion de right-sizing dans l'UI |
| **Region Alert** | Région `high` | Recommandation d'une alternative `low-carbon` |
| **Budget Gate** | Coût > seuil (défaut 50$) | Blocage du déploiement |
| **Disk Type Default** | Toute VM | `pd-standard` par défaut (pas SSD) |
| **Machine Family** | Recommandation Wizard | E2 (shared-core) en priorité |

---

## 7. Labels Terraform

Chaque ressource générée par EcoArch reçoit un label `carbon_awareness` :

| Condition | Label |
| :--- | :--- |
| Machine E2 (shared-core) | `carbon_awareness = "high"` |
| Machine N1/N2/C2 (dedicated) | `carbon_awareness = "standard"` |

Ces labels permettent un filtrage et un reporting dans la console GCP.

---

## 8. Sources & Références

| Source | URL |
| :--- | :--- |
| Google Cloud Carbon Footprint | https://cloud.google.com/carbon-footprint |
| Cloud Carbon Footprint (open source) | https://www.cloudcarbonfootprint.org/ |
| Teads Engineering Blog | https://engineering.teads.com/ |
| ADEME Base Carbone | https://base-empreinte.ademe.fr/ |
| GCP Region Picker (low carbon) | https://cloud.google.com/sustainability/region-carbon |

---

<p align="center"><i>Document généré dans le cadre du projet EcoArch — GreenOps & FinOps Platform</i></p>
