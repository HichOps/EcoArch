"""Simulateur de coûts infrastructure via Infracost et Terraform.

Sécurité :
- Toutes les valeurs utilisateur passent par des validateurs stricts (regex whitelist).
- Les variables Terraform sont injectées via des fichiers .tfvars.json (json.dumps),
  éliminant tout risque d'injection HCL.
- Les sous-processus reçoivent un environnement minimal (_safe_env), sans secrets applicatifs.
"""
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

from .config import Config, GCPConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Validation Patterns ──────────────────────────────────────────
_RE_DEPLOYMENT_ID = re.compile(r"^[a-z0-9][a-z0-9\-]{1,30}$")
_RE_SAFE_VALUE = re.compile(r"^[a-zA-Z0-9_\-./]+$")

# Whitelists strictes pour les valeurs Terraform
_ALLOWED_MACHINE_TYPES = set(GCPConfig.INSTANCE_TYPES) | {
    "e2-highcpu-2", "e2-highmem-2",
}
_ALLOWED_DB_TIERS = set(GCPConfig.DB_TIERS) | {"db-custom-2-3840"}
_ALLOWED_DB_VERSIONS = set(GCPConfig.DB_VERSIONS)
_ALLOWED_STORAGE_CLASSES = set(GCPConfig.STORAGE_CLASSES) | {"MULTI_REGIONAL"}
_ALLOWED_SOFTWARE_STACKS = set(GCPConfig.get_stack_names())


class ValidationError(ValueError):
    """Erreur de validation des entrées utilisateur."""
    pass


def _validate_deployment_id(value: str) -> str:
    """Valide et retourne un deployment_id sûr."""
    if not _RE_DEPLOYMENT_ID.match(value):
        raise ValidationError(
            f"deployment_id invalide (alphanum + tirets, 2-31 chars): {value!r}"
        )
    return value


def _validate_value(value: str, field_name: str, allowed: set[str] | None = None) -> str:
    """Valide une valeur Terraform contre une whitelist ou un pattern sûr."""
    if allowed and value not in allowed:
        raise ValidationError(
            f"{field_name} non autorisé: {value!r}. Valeurs acceptées: {sorted(allowed)}"
        )
    if not allowed and not _RE_SAFE_VALUE.match(value):
        raise ValidationError(
            f"{field_name} contient des caractères interdits: {value!r}"
        )
    return value


def _validate_int(value: Any, field_name: str, min_val: int = 1, max_val: int = 64000) -> int:
    """Valide un entier dans une plage autorisée."""
    try:
        v = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} doit être un entier: {value!r}")
    if not (min_val <= v <= max_val):
        raise ValidationError(f"{field_name} hors limites [{min_val}, {max_val}]: {v}")
    return v


@dataclass
class SimulationResult:
    """Résultat d'une simulation de coûts."""
    success: bool
    monthly_cost: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


# ── Fallback Pricing (GCP approximatif USD/mois) ─────────────
_FALLBACK_COMPUTE: dict[str, float] = {
    "e2-micro": 7.12, "e2-small": 14.23, "e2-medium": 29.38,
    "e2-standard-2": 58.76, "e2-standard-4": 117.51,
    "e2-standard-8": 235.03, "e2-standard-16": 470.05,
    "e2-highcpu-2": 50.96, "e2-highmem-2": 73.51,
    "n1-standard-1": 24.27, "n2-standard-2": 65.64,
    "n2-standard-4": 131.29, "c2-standard-4": 141.24,
}
_FALLBACK_DISK_PER_GB = 0.04  # SSD PD $/GB/mois

_FALLBACK_SQL: dict[str, float] = {
    "db-f1-micro": 7.67, "db-g1-small": 25.55,
    "db-custom-1-3840": 50.34, "db-custom-2-3840": 75.02,
    "db-custom-2-7680": 100.67, "db-custom-4-15360": 201.34,
}

_FALLBACK_STORAGE: dict[str, float] = {
    "STANDARD": 2.60, "NEARLINE": 1.30, "COLDLINE": 0.70,
    "ARCHIVE": 0.15, "MULTI_REGIONAL": 3.30,
}

_FALLBACK_LB = 18.26


def _fuzzy_lookup(table: dict[str, float], key: str, default: float) -> tuple[float, str]:
    """Recherche exacte puis par sous-chaîne dans une table de pricing.

    Retourne (prix, clé_trouvée). Si rien ne matche, retourne (default, key).
    """
    # 1. Exact match
    if key in table:
        return table[key], key

    # 2. Keyword match : la clé de la table est contenue dans key ou inversement
    key_lower = key.lower()
    for tbl_key, price in table.items():
        if tbl_key.lower() in key_lower or key_lower in tbl_key.lower():
            logger.info("Fuzzy match: '%s' → '%s'", key, tbl_key)
            return price, tbl_key

    logger.warning("Aucun prix trouvé pour '%s', défaut %.2f $", key, default)
    return default, key


def fallback_estimate(resources: list[dict[str, Any]]) -> SimulationResult:
    """Estimation hors-ligne basée sur le pricing public GCP.

    Utilisée quand Infracost n'est pas disponible ou échoue.
    """
    logger.info("Démarrage du calcul fallback pour %d ressources...", len(resources))

    total = 0.0
    breakdown: list[dict[str, Any]] = []

    for item in resources:
        # ── DEBUG : identifier le type réel de chaque élément ──
        logger.info(f"[DEBUG] Item type: {type(item)} - Content: {item}")

        # ── Blindage : normaliser l'item en dict ──
        if isinstance(item, dict):
            res = item
        elif isinstance(item, str):
            logger.warning("Item est une string '%s', wrapping en dict", item)
            res = {"type": "compute", "display_name": item}
        else:
            # Objet Reflex ou autre : tenter la conversion
            try:
                res = dict(item)  # type: ignore[arg-type]
                logger.info("Item converti via dict(): %s", res)
            except (TypeError, ValueError):
                try:
                    res = {k: getattr(item, k) for k in ("type", "display_name", "machine_type", "db_tier", "storage_class", "disk_size", "db_version") if hasattr(item, k)}
                    logger.info("Item converti via getattr: %s", res)
                except Exception as conv_err:
                    logger.error("Impossible de convertir l'item: %s", conv_err)
                    res = {"type": "unknown", "display_name": str(item)}

        rt = res.get("type", "compute")
        display = res.get("display_name", rt)
        cost = 0.0

        if rt == "compute":
            machine = res.get("machine_type", "e2-medium")
            vm_cost, matched = _fuzzy_lookup(_FALLBACK_COMPUTE, machine, 29.38)
            disk = int(res.get("disk_size", 50))
            cost = vm_cost + disk * _FALLBACK_DISK_PER_GB
        elif rt == "sql":
            tier = res.get("db_tier", "db-f1-micro")
            cost, matched = _fuzzy_lookup(_FALLBACK_SQL, tier, 7.67)
        elif rt == "storage":
            cls = res.get("storage_class", "STANDARD")
            cost, matched = _fuzzy_lookup(_FALLBACK_STORAGE, cls, 2.60)
        elif rt == "load_balancer":
            cost = _FALLBACK_LB
        else:
            cost = 1.0
            logger.warning("Type de ressource inconnu '%s' – forfait 1.00 $", rt)

        logger.info("Prix trouvé pour %s : %.2f $", display, cost)
        total += cost
        breakdown.append({
            "name": display,
            "monthlyCost": str(round(cost, 2)),
        })

    logger.info("Total final calculé : %.2f $", round(total, 2))

    # Safety net : si des ressources existent mais total <= 0, forcer 5 $
    # pour rendre le problème visible si le fallback échoue
    if resources and total <= 0.0:
        total = 5.0
        logger.warning("Safety net appliqué : total forcé à 5.00 $ (cart non vide mais coût <= 0)")

    details = {
        "totalMonthlyCost": str(round(total, 2)),
        "projects": [{"breakdown": {"resources": breakdown}}],
        "_source": "fallback",
    }
    return SimulationResult(
        success=True,
        monthly_cost=round(total, 2),
        details=details,
    )


class InfracostSimulator:
    """Simule et déploie des ressources GCP avec estimation des coûts."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.project_id = project_id or Config.GCP_PROJECT_ID
        self.timeout = timeout or Config.INFRACOST_TIMEOUT

    # ── Environnement sécurisé pour les sous-processus ────────────

    @staticmethod
    def _safe_env() -> dict[str, str]:
        """Construit un environnement minimal pour Terraform/Infracost.

        Seules les variables strictement nécessaires sont transmises.
        Les secrets applicatifs (SUPABASE_*, REDIS_URL, etc.) sont exclus.
        """
        allowed_keys = {
            "PATH", "HOME", "LANG", "TERM", "USER", "SHELL",
            # Terraform / GCP
            "TF_IN_AUTOMATION", "TF_LOG",
            "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT",
            "CLOUDSDK_CONFIG",
            # Infracost
            "INFRACOST_API_KEY",
        }
        env = {k: v for k, v in os.environ.items() if k in allowed_keys}
        env["TF_IN_AUTOMATION"] = "true"
        return env

    # ── Validation des ressources ─────────────────────────────────

    def _validate_resource(self, res: dict[str, Any]) -> dict[str, Any]:
        """Valide et normalise une ressource avant génération Terraform."""
        resource_type = res.get("type", "compute")
        _validate_value(resource_type, "type", {"compute", "sql", "storage", "load_balancer"})

        validated: dict[str, Any] = {"type": resource_type}

        if resource_type == "compute":
            validated["machine_type"] = _validate_value(
                res.get("machine_type", "e2-medium"), "machine_type", _ALLOWED_MACHINE_TYPES
            )
            validated["disk_size"] = _validate_int(
                res.get("disk_size", 50), "disk_size", min_val=10, max_val=64000
            )
            validated["software_stack"] = _validate_value(
                res.get("software_stack", "none"), "software_stack", _ALLOWED_SOFTWARE_STACKS
            )
        elif resource_type == "sql":
            validated["db_tier"] = _validate_value(
                res.get("db_tier", "db-f1-micro"), "db_tier", _ALLOWED_DB_TIERS
            )
            validated["db_version"] = _validate_value(
                res.get("db_version", "POSTGRES_14"), "db_version", _ALLOWED_DB_VERSIONS
            )
        elif resource_type == "storage":
            validated["storage_class"] = _validate_value(
                res.get("storage_class", "STANDARD"), "storage_class", _ALLOWED_STORAGE_CLASSES
            )
        # load_balancer has no user-controlled fields

        return validated

    # ── Génération Terraform sécurisée (tfvars.json) ──────────────

    def _generate_terraform_files(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str = "simulation",
        include_backend: bool = True,
        tmpdir: str = "",
    ) -> None:
        """Génère main.tf (structure fixe) + terraform.tfvars.json (valeurs).

        Architecture de sécurité :
        - main.tf contient UNIQUEMENT des références à des variables (var.xxx)
        - terraform.tfvars.json contient les valeurs, sérialisées via json.dumps()
        - Aucune interpolation f-string de valeurs utilisateur dans le HCL
        """
        deployment_id = _validate_deployment_id(deployment_id)
        validated_resources = [self._validate_resource(r) for r in resources]

        # ── 1. Construire les variables tfvars ────────────────────
        tfvars: dict[str, Any] = {
            "project_id": self.project_id,
            "region": Config.DEFAULT_REGION,
            "deployment_id": deployment_id,
            "state_bucket": Config.TERRAFORM_STATE_BUCKET,
            "default_image": Config.DEFAULT_IMAGE,
        }

        compute_resources = []
        sql_resources = []
        storage_resources = []
        lb_count = 0

        for idx, res in enumerate(validated_resources):
            rt = res["type"]
            if rt == "compute":
                startup_script = GCPConfig.get_startup_script(res["software_stack"])
                compute_resources.append({
                    "name": f"res-{idx}-compute",
                    "gcp_name": f"res-{idx}-compute-{deployment_id}",
                    "machine_type": res["machine_type"],
                    "disk_size": res["disk_size"],
                    "software_stack": res["software_stack"],
                    "startup_script": startup_script,
                    "zone": f"{Config.DEFAULT_REGION}-a",
                })
            elif rt == "sql":
                sql_resources.append({
                    "name": f"res-{idx}-sql",
                    "gcp_name": f"res-{idx}-sql-{deployment_id}",
                    "db_tier": res["db_tier"],
                    "db_version": res["db_version"],
                })
            elif rt == "storage":
                safe_bucket = f"{self.project_id}-res-{idx}-storage-{deployment_id}".lower()
                storage_resources.append({
                    "name": f"res-{idx}-storage",
                    "bucket_name": safe_bucket,
                    "storage_class": res["storage_class"],
                })
            elif rt == "load_balancer":
                lb_count += 1

        tfvars["compute_instances"] = compute_resources
        tfvars["sql_instances"] = sql_resources
        tfvars["storage_buckets"] = storage_resources
        tfvars["lb_count"] = lb_count

        # ── 2. Écrire terraform.tfvars.json ───────────────────────
        tfvars_path = Path(tmpdir) / "terraform.tfvars.json"
        tfvars_path.write_text(json.dumps(tfvars, indent=2))

        # ── 3. Écrire main.tf (structure fixe) ────────────────────
        main_tf = self._generate_static_hcl(include_backend)
        tf_path = Path(tmpdir) / "main.tf"
        tf_path.write_text(main_tf)

    def _generate_static_hcl(self, include_backend: bool) -> str:
        """Génère le HCL statique avec uniquement des var.xxx references.

        Ce fichier ne contient AUCUNE valeur utilisateur interpolée.
        Toutes les valeurs proviennent de terraform.tfvars.json.
        """
        backend_block = ""
        if include_backend:
            backend_block = """
  backend "gcs" {}"""

        return '''# ═══════════════════════════════════════════════════
# EcoArch – Terraform Config (auto-generated)
# Valeurs injectées via terraform.tfvars.json
# ═══════════════════════════════════════════════════

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }''' + backend_block + '''
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Variables ─────────────────────────────────────
variable "project_id" { type = string }
variable "region" { type = string }
variable "deployment_id" { type = string }
variable "state_bucket" { type = string; default = "" }
variable "default_image" { type = string; default = "debian-cloud/debian-11" }
variable "lb_count" { type = number; default = 0 }

variable "compute_instances" {
  type = list(object({
    name           = string
    gcp_name       = string
    machine_type   = string
    disk_size      = number
    software_stack = string
    startup_script = string
    zone           = string
  }))
  default = []
}

variable "sql_instances" {
  type = list(object({
    name       = string
    gcp_name   = string
    db_tier    = string
    db_version = string
  }))
  default = []
}

variable "storage_buckets" {
  type = list(object({
    name          = string
    bucket_name   = string
    storage_class = string
  }))
  default = []
}

# ── Compute Engine ────────────────────────────────
resource "google_compute_instance" "vm" {
  count        = length(var.compute_instances)
  name         = var.compute_instances[count.index].gcp_name
  machine_type = var.compute_instances[count.index].machine_type
  zone         = var.compute_instances[count.index].zone

  boot_disk {
    initialize_params {
      image = var.default_image
      size  = var.compute_instances[count.index].disk_size
    }
  }

  network_interface { network = "default" }

  dynamic "metadata" {
    for_each = var.compute_instances[count.index].startup_script != "" ? [1] : []
    content {
      startup-script = var.compute_instances[count.index].startup_script
    }
  }

  labels = {
    deployment_id  = var.deployment_id
    managed_by     = "ecoarch-app"
    software_stack = var.compute_instances[count.index].software_stack
  }
}

# ── Cloud SQL ─────────────────────────────────────
resource "google_sql_database_instance" "db" {
  count            = length(var.sql_instances)
  name             = var.sql_instances[count.index].gcp_name
  database_version = var.sql_instances[count.index].db_version
  region           = var.region
  settings { tier = var.sql_instances[count.index].db_tier }
  deletion_protection = false
}

# ── Cloud Storage ─────────────────────────────────
resource "google_storage_bucket" "bucket" {
  count         = length(var.storage_buckets)
  name          = var.storage_buckets[count.index].bucket_name
  location      = var.region
  storage_class = var.storage_buckets[count.index].storage_class
  force_destroy = true
}

# ── Load Balancer ─────────────────────────────────
resource "google_compute_global_address" "lb" {
  count = var.lb_count
  name  = "lb-ip-${var.deployment_id}-${count.index}"
}
'''

    # ── Backward compat: _generate_terraform_code for tests ───────

    def _generate_terraform_code(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str = "simulation",
        include_backend: bool = True,
    ) -> str:
        """Generates Terraform files and returns the main.tf + tfvars content.

        Kept for backward compatibility with existing test suite.
        Internally delegates to the secure _generate_terraform_files method.
        """
        with tempfile.TemporaryDirectory(prefix="ecoarch_compat_") as tmpdir:
            try:
                self._generate_terraform_files(
                    resources, deployment_id, include_backend, tmpdir
                )
            except ValidationError:
                # For compat: if deployment_id fails validation, use a safe default
                safe_id = re.sub(r"[^a-z0-9\-]", "", deployment_id.lower()) or "sim"
                if not re.match(r"^[a-z0-9]", safe_id):
                    safe_id = "x" + safe_id
                self._generate_terraform_files(
                    resources, safe_id[:31], include_backend, tmpdir
                )

            tf_path = Path(tmpdir) / "main.tf"
            tfvars_path = Path(tmpdir) / "terraform.tfvars.json"

            parts = [tf_path.read_text()]
            if tfvars_path.exists():
                parts.append(f"\n# === tfvars.json ===\n# {tfvars_path.read_text()}")
            return "\n".join(parts)

    # ── Méthodes publiques ────────────────────────────────────────

    def simulate(self, resources: list[dict[str, Any]]) -> SimulationResult:
        """Simule les coûts des ressources via Infracost.

        Si Infracost n'est pas disponible ou échoue, retombe
        automatiquement sur l'estimation hors-ligne (fallback).
        """
        if not resources:
            return SimulationResult(success=True, monthly_cost=0.0, details={})

        try:
            with tempfile.TemporaryDirectory(prefix=Config.TEMP_FILE_PREFIX) as tmpdir:
                self._generate_terraform_files(
                    resources, "simulation-tmp", include_backend=False, tmpdir=tmpdir
                )

                result = subprocess.run(
                    ["infracost", "breakdown", "--path", tmpdir, "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=self._safe_env(),
                    check=False,
                )

                if result.returncode != 0:
                    logger.info(
                        "Infracost indisponible (exit %d), utilisation du fallback",
                        result.returncode,
                    )
                    return fallback_estimate(resources)

                try:
                    data = json.loads(result.stdout)
                    raw_cost = data.get("totalMonthlyCost", 0.0)
                    cost = float(raw_cost)
                    logger.info(
                        "[DEBUG] Infracost exit 0 – raw totalMonthlyCost=%r, parsed=%.2f",
                        raw_cost, cost,
                    )

                    # Si Infracost retourne 0 pour un panier non-vide,
                    # il n'a probablement pas d'API key → utiliser le fallback
                    if cost <= 0.0 and resources:
                        logger.warning(
                            "Infracost a retourné 0 $ pour %d ressources, "
                            "basculement sur le fallback",
                            len(resources),
                        )
                        return fallback_estimate(resources)

                    return SimulationResult(
                        success=True,
                        monthly_cost=cost,
                        details=data,
                    )
                except (json.JSONDecodeError, ValueError) as parse_err:
                    logger.warning(
                        "Infracost JSON invalide (%s), utilisation du fallback",
                        parse_err,
                    )
                    return fallback_estimate(resources)

        except subprocess.TimeoutExpired:
            logger.warning("Infracost timeout, utilisation du fallback")
            return fallback_estimate(resources)
        except ValidationError as e:
            return SimulationResult(success=False, error_message=f"Validation: {e}")
        except Exception as e:
            logger.warning("Infracost erreur (%s), utilisation du fallback", e)
            return fallback_estimate(resources)

    def deploy(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str,
    ) -> Generator[str, None, None]:
        """Déploie les ressources via Terraform (générateur pour streaming)."""
        deployment_id = _validate_deployment_id(deployment_id)

        with tempfile.TemporaryDirectory(prefix=f"ecoarch_{deployment_id}_") as tmpdir:
            yield f"📝 ID: {deployment_id}"

            self._generate_terraform_files(resources, deployment_id, tmpdir=tmpdir)

            # Init
            yield "⚙️ Terraform init..."
            yield from self._run_terraform(tmpdir, ["init", "-input=false", "-no-color", "-reconfigure"])

            # Apply
            yield "🚀 Terraform apply..."
            yield from self._run_terraform(tmpdir, ["apply", "-auto-approve", "-input=false", "-no-color"])

            yield "✅ Déploiement terminé"

    def destroy(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str,
    ) -> Generator[str, None, None]:
        """Détruit les ressources via Terraform (générateur pour streaming)."""
        deployment_id = _validate_deployment_id(deployment_id)

        with tempfile.TemporaryDirectory(prefix=f"ecoarch_destroy_{deployment_id}_") as tmpdir:
            yield f"🔥 Cible: {deployment_id}"

            self._generate_terraform_files([], deployment_id, tmpdir=tmpdir)

            # Init
            yield "⏳ Connexion au state..."
            for line in self._run_terraform(tmpdir, ["init", "-input=false", "-no-color", "-reconfigure"]):
                yield f"Init > {line}"

            # Destroy
            yield "⚠️ Destruction en cours..."
            for line in self._run_terraform(
                tmpdir,
                ["destroy", "-auto-approve", "-input=false", "-lock=false", "-no-color"],
            ):
                if line.strip():
                    yield f"Destroy > {line}"

            yield "🗑️ Nettoyage terminé"

    def _run_terraform(
        self,
        cwd: str,
        args: list[str],
    ) -> Generator[str, None, None]:
        """Exécute une commande Terraform avec streaming des logs et timeout."""
        process = subprocess.Popen(
            ["terraform", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self._safe_env(),
            bufsize=1,
        )

        for line in process.stdout:
            yield line.strip()

        try:
            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            logger.error(
                "Terraform %s timed out after %ds – killing process (PID %d)",
                args[0], self.timeout, process.pid,
            )
            process.kill()
            remaining = process.stdout.read() if process.stdout else ""
            if remaining:
                for tail_line in remaining.strip().splitlines()[-5:]:
                    yield f"[TIMEOUT TAIL] {tail_line.strip()}"
            process.wait()
            raise Exception(
                f"Terraform {args[0]} timed out after {self.timeout}s"
            )

        if process.returncode != 0:
            raise Exception(f"Terraform {args[0]} failed (exit {process.returncode})")
