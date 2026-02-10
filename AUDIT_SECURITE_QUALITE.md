# 🛡️ AUDIT COMPLET – SÉCURITÉ, QUALITÉ & MAINTENABILITÉ

**Projet :** EcoArch – Simulateur FinOps GCP  
**Version auditée :** v1.1.1 (Cloud Run revision `00020-gjv`)  
**Date :** Juin 2025  
**Auditeur :** Senior Software Architect & Cybersecurity Expert  

---

## 📊 BILAN GLOBAL : 6.2 / 10

| Axe                  | Note  | Verdict                         |
|----------------------|-------|---------------------------------|
| 🔒 Sécurité          | 4/10  | ⛔ **Insuffisant** – failles critiques    |
| 🧹 Clean Code        | 6/10  | ⚠️ Passable – dette technique présente  |
| 💪 Robustesse        | 7/10  | ✅ Correct – bonne gestion des erreurs  |
| 🏗️ Maintenabilité    | 7/10  | ✅ Correct – architecture lisible       |
| 🧪 Tests             | 6.5/10| ⚠️ Passable – couverture incomplète    |

> **Synthèse** : L'application est fonctionnelle et bien structurée pour un MVP.
> La séparation backend/frontend, le pattern Secret Manager et l'industrialisation
> Celery sont de bon niveau. **Cependant, des failles de sécurité critiques empêchent
> toute mise en production réelle** (injection HCL, absence d'authentification,
> fuite de secrets dans les sous-processus).

---

## 🔴 POINTS CRITIQUES (À corriger immédiatement)

### CRIT-1 · Injection HCL / Terraform (CVSS ~8.5)

**Fichier :** [src/simulation.py](src/simulation.py#L87-L170)

Le `deployment_id` et toutes les valeurs utilisateur (`machine_type`, `db_tier`, `storage_class`, `software_stack`) sont interpolés directement dans du code Terraform via f-strings **sans aucune validation ni sanitization**.

```python
# simulation.py L98 – deployment_id injecté tel quel
gcp_name = f"{name}-{deployment_id}"
# simulation.py L120
machine = res.get("machine_type", "e2-medium")
return f'machine_type = "{machine}"'
```

**Impact :** Un utilisateur peut injecter du code HCL arbitraire via le champ `deployment_id` ou `machine_type`, permettant :
- Création de ressources non autorisées sur le projet GCP
- Exfiltration de secrets via `data "http"` ou `external` providers
- Destruction de ressources existantes

**Correction :**
```python
import re

_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{2,20}$")
_SAFE_VALUE_RE = re.compile(r"^[a-zA-Z0-9_\-./]+$")

def _validate_deployment_id(value: str) -> str:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"deployment_id invalide: {value!r}")
    return value

def _validate_tf_value(value: str, field: str) -> str:
    if not _SAFE_VALUE_RE.match(value):
        raise ValueError(f"{field} contient des caractères interdits: {value!r}")
    return value
```

---

### CRIT-2 · Fuite de secrets dans les sous-processus (CVSS ~7.0)

**Fichier :** [src/simulation.py](src/simulation.py#L211) et [ligne 317](src/simulation.py#L317)

```python
# simulation.py – L211 & L317
env=os.environ,  # ← TOUT l'environnement est passé
```

L'intégralité de `os.environ` est transmise à `subprocess.run()` et `subprocess.Popen()`, incluant `SUPABASE_SERVICE_KEY`, `INFRACOST_API_KEY`, `REDIS_URL`, et tout autre secret présent.

**Impact :** Si Terraform écrit un crash dump ou si un provider malveillant est chargé, les secrets sont exposés.

**Correction :**
```python
def _safe_env(self) -> dict[str, str]:
    """Environnement minimal pour les sous-processus Terraform."""
    allowed = {"PATH", "HOME", "LANG", "TERM", "TF_IN_AUTOMATION",
               "INFRACOST_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"}
    return {k: v for k, v in os.environ.items() if k in allowed}
```

---

### CRIT-3 · Absence totale d'authentification (CVSS ~9.0)

**Fichier :** [frontend/frontend/state.py](frontend/frontend/state.py#L81-L85)

```python
current_user: str = "Alice (DevOps)"
users_list: list[str] = [
    "Alice (DevOps)", "Bob (FinOps)", "Charlie (Manager)", "Dave (Admin)"
]
```

La liste des utilisateurs est **hardcodée côté client**. N'importe qui accédant à l'URL peut :
- Sélectionner un utilisateur arbitraire
- Lancer un déploiement Terraform sur le projet GCP
- Détruire des ressources existantes
- Consommer du budget cloud sans contrôle

**Impact :** Déploiement/destruction de ressources GCP par n'importe quel visiteur anonyme.

**Correction :** Intégrer un fournisseur d'identité (Google IAP sur Cloud Run, Firebase Auth, ou Supabase Auth) et ajouter un middleware de vérification de session.

---

### CRIT-4 · Mot de passe MySQL root hardcodé (CVSS ~6.0)

**Fichier :** [src/config.py](src/config.py#L237-L245)

```python
# LAMP & LEMP stacks
debconf-set-selections <<< 'mysql-server mysql-server/root_password password root'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password root'
```

Le mot de passe MySQL root est `root` dans les scripts de démarrage LAMP/LEMP. Ce script est injecté dans les métadonnées de la VM GCP et exécuté au boot.

**Correction :** Générer un mot de passe aléatoire au runtime :
```bash
MYSQL_ROOT_PASS=$(openssl rand -base64 24)
debconf-set-selections <<< "mysql-server mysql-server/root_password password ${MYSQL_ROOT_PASS}"
```

---

### CRIT-5 · Risque SSRF dans le commentaire GitLab

**Fichier :** [src/gitlab_comment.py](src/gitlab_comment.py#L23-L38)

```python
server_url = os.getenv("CI_SERVER_URL")
url = f"{server_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
response = requests.post(url, ...)
```

`CI_SERVER_URL` est lu sans validation. Si un attaquant contrôle cette variable, il peut rediriger la requête (avec le `GITLAB_TOKEN` en header) vers un serveur arbitraire.

**Correction :**
```python
from urllib.parse import urlparse

def _validate_gitlab_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        raise ValueError("GitLab URL must use HTTPS")
    if not parsed.hostname:
        raise ValueError("Invalid GitLab URL")
    return url
```

---

## 🟡 AMÉLIORATIONS SUGGÉRÉES (Clean Code & Architecture)

### ARCH-1 · Fallback classes massifs dans state.py (DRY)

**Fichier :** [frontend/frontend/state.py](frontend/frontend/state.py#L22-L73)

Le bloc `except ImportError` duplique 50 lignes de stub classes. Cela viole le principe DRY et crée un risque de divergence silencieuse avec les vraies classes.

**Correction :** Extraire les stubs dans un module dédié `src/stubs.py` ou utiliser un pattern factory :
```python
try:
    from src.config import GCPConfig, Config
except ImportError:
    from src.stubs import GCPConfig, Config  # Module léger pour dev sans backend
```

---

### ARCH-2 · `sys.path.append()` fragile

**Fichier :** [frontend/frontend/state.py](frontend/frontend/state.py#L11-L12)

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))
```

Ce hack rend les imports dépendants de la structure de fichiers et peut créer des conflits de modules.

**Correction :** Transformer le projet en package installable avec un `pyproject.toml` et utiliser `pip install -e .` en dev.

---

### ARCH-3 · Connexion Supabase sans pooling

**Fichier :** [frontend/frontend/state.py](frontend/frontend/state.py#L512-L540)

Un nouveau `create_client()` est instancié **à chaque appel** d'audit log. Avec 10 actions simultanées, cela crée 10 connexions HTTP distinctes.

**Correction :**
```python
# Module-level singleton
_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is None and Config.SUPABASE_URL:
        _supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    return _supabase_client
```

---

### ARCH-4 · `print()` au lieu de `logging`

**Fichiers :** [src/parser.py](src/parser.py), [src/budget_gate.py](src/budget_gate.py), [src/gitlab_comment.py](src/gitlab_comment.py)

Ces 3 modules utilisent `print()` pour les messages de diagnostic. En production, ces sorties sont perdues ou mélangées avec les logs structurés.

**Correction :** Remplacer tous les `print()` par `logger.info()` / `logger.error()` avec un logger nommé.

---

### ARCH-5 · Imports cassés dans budget_gate.py et gitlab_comment.py

**Fichiers :** [src/budget_gate.py](src/budget_gate.py#L5), [src/gitlab_comment.py](src/gitlab_comment.py#L6)

```python
from parser import EcoArchParser  # ❌ Devrait être: from src.parser
```

Ces imports fonctionnent uniquement quand le script est lancé depuis la racine avec `PYTHONPATH=.`. Ils échouent quand le module est importé comme package.

**Correction :** `from src.parser import EcoArchParser` ou `from .parser import EcoArchParser`.

---

### ARCH-6 · `sys.exit()` dans du code bibliothèque

**Fichier :** [src/budget_gate.py](src/budget_gate.py#L32-L36)

```python
if total_cost > budget_limit:
    sys.exit(1)  # ← Tue le process entier
```

`sys.exit()` dans une fonction de bibliothèque rend le code impossible à réutiliser (ex: dans les tests, ou si appelé depuis l'app).

**Correction :**
```python
class BudgetExceededError(Exception):
    pass

def check_budget() -> bool:
    ...
    if total_cost > budget_limit:
        raise BudgetExceededError(f"Budget exceeded by {excess:.2f}")
    return True

if __name__ == "__main__":
    try:
        check_budget()
    except BudgetExceededError:
        sys.exit(1)
```

---

### ARCH-7 · `REDIS_URL` lu hors de Config

**Fichier :** [src/tasks.py](src/tasks.py#L20)

```python
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

La même variable existe dans `Config.REDIS_URL`. Ce doublon crée un risque de divergence.

**Correction :** `from src.config import Config` puis `REDIS_URL = Config.REDIS_URL`.

---

### ARCH-8 · `load_dotenv()` à l'import de config.py

**Fichier :** [src/config.py](src/config.py#L6)

```python
load_dotenv()  # Side effect au module level
```

Cela charge un fichier `.env` dès qu'un module importe `Config`, ce qui peut écraser des variables d'environnement en production.

**Correction :**
```python
load_dotenv(override=False)  # Ne pas écraser les vars déjà définies
```

---

### ARCH-9 · `MAX_STORAGE_GB` mal placé

**Fichier :** [src/config.py](src/config.py#L290)

```python
    @classmethod
    def get_startup_script(cls, stack_id: str) -> str:
        ...
    MAX_STORAGE_GB = 64000  # ← Après la méthode, visuellement confus
```

**Correction :** Remonter la constante avec les autres attributs de classe (après `MIN_STORAGE_GB`).

---

### ARCH-10 · Couplage frontend → backend dans pricing.py

**Fichier :** [frontend/frontend/components/pricing.py](frontend/frontend/components/pricing.py)

Ce composant frontend importe directement `from src.config import Config` pour accéder aux noms de stacks.

**Correction :** Passer les données via le `State` Reflex (déjà fait pour `instance_types`, etc.) plutôt qu'importer `src.config` dans le frontend.

---

## 🟠 ROBUSTESSE – Points d'attention

### ROB-1 · `except Exception: pass` silencieux

**Fichier :** [frontend/frontend/state.py](frontend/frontend/state.py#L549-L550)

```python
def _update_audit_log(self, audit_id, status):
    ...
    except Exception:
        pass  # ← Erreur Supabase ignorée silencieusement
```

**Impact :** Un problème de connexion Supabase passe totalement inaperçu. Les audit logs peuvent être silencieusement perdus sans alerte.

**Correction :** Au minimum `logger.warning("Audit log update failed", exc_info=True)`.

---

### ROB-2 · `except Exception: pass` dans load_audit_logs et chart_data

**Fichiers :** [state.py L564](frontend/frontend/state.py#L564), [state.py L600](frontend/frontend/state.py#L600)

Même pattern de suppression silencieuse d'erreurs. Ces 3 `pass` cumulés rendent le débogage en production très difficile.

---

### ROB-3 · Pas de retry/backoff sur les appels Supabase

Les appels à Supabase (insert audit, load logs, save metrics) ne gèrent pas les erreurs transitoires (timeout réseau, rate limit). Un simple retry avec backoff exponentiel améliorerait la fiabilité.

---

### ROB-4 · stderr non capturé dans _run_terraform

**Fichier :** [src/simulation.py](src/simulation.py#L306)

```python
stderr=subprocess.STDOUT,  # Merge stderr dans stdout
```

C'est acceptable, mais les erreurs Terraform sont mélangées avec les logs normaux, rendant le parsing des erreurs plus difficile.

---

## 🧪 TESTS – Analyse de couverture

| Module                  | Tests | Verdict                             |
|-------------------------|-------|-------------------------------------|
| `src/simulation.py`     | 20    | ✅ Bien couvert                      |
| `src/parser.py`         | 3     | ⚠️ Basique                          |
| `frontend/state.py`     | 24    | ✅ Bien couvert (wizard, cart, audit) |
| `src/config.py`         | 0     | ❌ Non testé                         |
| `src/recommendation.py` | 0     | ❌ Non testé                         |
| `src/tasks.py`          | 0     | ❌ Non testé                         |
| `src/budget_gate.py`    | 0     | ❌ Non testé                         |
| `src/gitlab_comment.py` | 0     | ❌ Non testé                         |

**Total : 47 tests, ~55% de couverture de code estimée.**

Tests manquants critiques :
- `recommendation.py` : Tester les combinaisons `(env × traffic × workload × criticality)`
- `tasks.py` : Tester `_sanitize_log_line()` avec des patterns de secrets réels
- `config.py` : Tester `_get_secret_or_env()`, `_is_running_in_gcp()`
- Validation des inputs (quand elle sera implémentée)

---

## 🔧 CI/CD – Points faibles

### CI-1 · mypy ignoré silencieusement

**Fichier :** [.gitlab-ci.yml](RAPPORT_DEPLOIEMENT.md) (stage test)

```yaml
- mypy src/ --ignore-missing-imports || true
```

Le `|| true` fait que les erreurs de typage ne bloquent jamais le pipeline. Mypy devient un outil décoratif.

**Correction :** Supprimer `|| true` et corriger les erreurs mypy. Si transitoire, utiliser `allow_failure: true` sur le job pour distinguer.

---

### CI-2 · Aucun scan de sécurité

Le pipeline ne contient aucune étape de :
- **Dependency audit** (`pip-audit`, `safety`)
- **SAST** (semgrep, bandit)
- **Container scanning** (trivy, grype)

**Correction :** Ajouter un stage `security` :
```yaml
security:
  stage: test
  script:
    - pip install pip-audit bandit
    - pip-audit -r requirements.txt
    - bandit -r src/ -f json -o bandit-report.json
```

---

### CI-3 · ruff ignoré silencieusement

```yaml
- ruff check src/ tests/ --output-format=gitlab > ruff-report.json || true
```

Même problème que mypy – ruff ne bloque jamais.

---

## 🏗️ INFRASTRUCTURE – Observations

| Point                                | Status |
|--------------------------------------|--------|
| Multi-stage Dockerfile               | ✅      |
| Non-root user (`ecoarch`, UID 1000)  | ✅      |
| Secret Manager en prod               | ✅      |
| `.dockerignore` restrictif           | ✅      |
| `deploy.sh` avec smoke tests         | ✅      |
| `--allow-unauthenticated` Cloud Run  | ⚠️ Attendu pour un MVP, à revoir |
| `gcp-key.json` dans le repo          | 🔴 **CRITIQUE** – à supprimer immédiatement |

### ⚠️ `gcp-key.json` dans le dépôt

Un fichier `gcp-key.json` est présent à la racine du repo. Même s'il est ignoré par `.dockerignore`, sa présence dans Git est un risque majeur. Il faut :
1. Révoquer la clé immédiatement dans la console GCP
2. Supprimer le fichier et l'ajouter à `.gitignore`
3. Purger l'historique Git avec `git filter-branch` ou `bfg`

---

## 📋 PLAN D'ACTION

### Phase 1 – Sécurité critique (Jour 1-2)

| #   | Action                                            | Fichier(s)            | Effort |
|-----|---------------------------------------------------|-----------------------|--------|
| 1.1 | Valider/sanitizer `deployment_id` + valeurs TF    | `simulation.py`       | 2h     |
| 1.2 | Environnement minimal dans subprocess              | `simulation.py`       | 30min  |
| 1.3 | Supprimer `gcp-key.json` + purger historique Git  | repo root             | 1h     |
| 1.4 | Générer mot de passe MySQL aléatoire              | `config.py`           | 15min  |
| 1.5 | Valider `CI_SERVER_URL` (anti-SSRF)               | `gitlab_comment.py`   | 30min  |

### Phase 2 – Authentification (Jour 3-5)

| #   | Action                                            | Fichier(s)            | Effort |
|-----|---------------------------------------------------|-----------------------|--------|
| 2.1 | Intégrer Google IAP ou Supabase Auth               | `state.py`, Cloud Run | 1j     |
| 2.2 | Ajouter middleware de vérification de session       | `frontend.py`         | 4h     |
| 2.3 | Supprimer la liste d'utilisateurs hardcodée         | `state.py`            | 30min  |

### Phase 3 – Clean code & robustesse (Jour 6-8)

| #   | Action                                            | Fichier(s)                | Effort |
|-----|---------------------------------------------------|---------------------------|--------|
| 3.1 | Remplacer `print()` par `logging`                  | `parser.py`, `budget_gate.py`, `gitlab_comment.py` | 1h |
| 3.2 | Corriger `from parser` → `from src.parser`         | `budget_gate.py`, `gitlab_comment.py` | 15min |
| 3.3 | Extraire stubs dans `src/stubs.py`                 | `state.py`                | 1h     |
| 3.4 | Singleton Supabase client                          | `state.py`                | 30min  |
| 3.5 | Remplacer `except: pass` par `logger.warning`      | `state.py`                | 30min  |
| 3.6 | `load_dotenv(override=False)`                      | `config.py`               | 5min   |
| 3.7 | `sys.exit()` → exception dans `budget_gate.py`     | `budget_gate.py`          | 30min  |
| 3.8 | `REDIS_URL` via `Config` dans `tasks.py`           | `tasks.py`                | 10min  |
| 3.9 | Remonter `MAX_STORAGE_GB`                          | `config.py`               | 5min   |
| 3.10| `pyproject.toml` pour éliminer `sys.path.append`   | racine projet             | 2h     |

### Phase 4 – Tests & CI (Jour 9-12)

| #   | Action                                            | Fichier(s)            | Effort |
|-----|---------------------------------------------------|-----------------------|--------|
| 4.1 | Tests pour `recommendation.py` (8 cas)             | `tests/`              | 2h     |
| 4.2 | Tests pour `_sanitize_log_line` dans `tasks.py`    | `tests/`              | 1h     |
| 4.3 | Tests pour `config.py` (Secret Manager mock)       | `tests/`              | 2h     |
| 4.4 | Tests d'injection HCL (fuzzing basique)            | `tests/`              | 2h     |
| 4.5 | Supprimer `|| true` sur mypy et ruff               | `.gitlab-ci.yml`      | 30min  |
| 4.6 | Ajouter `pip-audit` + `bandit` dans la CI          | `.gitlab-ci.yml`      | 1h     |
| 4.7 | Objectif couverture : 80%+                         | `pyproject.toml`      | —      |

---

## 🏆 POINTS POSITIFS

| Élément                                              | Appréciation |
|------------------------------------------------------|-------------|
| Pattern `_get_secret_or_env()` avec Secret Manager   | 🌟 Excellent |
| Multi-stage Dockerfile avec non-root user            | 🌟 Excellent |
| `deploy.sh` avec auto-versioning et smoke tests      | 🌟 Très bon  |
| `_sanitize_log_line()` dans tasks.py                 | 🌟 Très bon  |
| Celery avec `task_acks_late` + `time_limit`          | 🌟 Très bon  |
| Timeout handling dans `_run_terraform`               | ✅ Bon       |
| 47 tests avec duck-typing Reflex workaround          | ✅ Bon       |
| Architecture séparée `src/` / `frontend/` / `tests/` | ✅ Bon       |
| `tempfile.TemporaryDirectory` pour isolation TF       | ✅ Bon       |
| `RecommendationEngine` clean et testable              | ✅ Bon       |

---

> **Conclusion** : EcoArch est un MVP fonctionnel avec une bonne fondation architecturale.
> Les **5 failles critiques** (injection HCL, fuite de secrets, absence d'auth, mot de passe
> hardcodé, SSRF) doivent être corrigées **avant toute exposition à des utilisateurs réels**.
> Le plan d'action en 4 phases (12 jours) permettrait d'atteindre un niveau **8/10**
> suffisant pour une mise en production encadrée.
