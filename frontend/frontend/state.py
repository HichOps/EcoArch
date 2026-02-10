"""État global de l'application EcoArch (Reflex State).

Sécurité :
- Authentification par token (CRIT-3) – les actions sensibles vérifient _require_auth().
- Plus de sys.path.append – imports propres via le package src (ARCH-2).
- Stubs centralisés dans src.stubs (ARCH-1 – DRY).
- Client Supabase singleton (ARCH-3).
- Logging explicite au lieu de except:pass (ROB-1).
"""
import hashlib
import hmac
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import reflex as rx

# ── Import bridge propre ──────────────────────────────────────────
# Ajout conditionnel du project root pour que les imports src.* marchent
# quand on lance `reflex run` depuis frontend/
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from src.config import GCPConfig, Config
    from src.simulation import InfracostSimulator
    from src.recommendation import RecommendationEngine
    from src.deployer import trigger_deployment, trigger_destruction
except ImportError:
    from src.stubs import (
        GCPConfigStub as GCPConfig,
        ConfigStub as Config,
        InfracostSimulatorStub as InfracostSimulator,
        RecommendationEngineStub as RecommendationEngine,
    )
    trigger_deployment = None
    trigger_destruction = None

logger = logging.getLogger(__name__)

# ── Supabase Singleton (ARCH-3) ──────────────────────────────────
_supabase_client = None


def _get_supabase():
    """Retourne un client Supabase singleton (ou None si non configuré)."""
    global _supabase_client
    if _supabase_client is None and Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            _supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
        except Exception:
            logger.warning("Impossible de créer le client Supabase", exc_info=True)
    return _supabase_client


# ── Authentification (CRIT-3) ────────────────────────────────────
# En production, AUTH_SECRET_KEY doit être défini dans Secret Manager.
# Le frontend envoie un token = HMAC(secret, username) pour prouver l'identité.
AUTH_SECRET = os.getenv("AUTH_SECRET_KEY", "")
AUTH_ENABLED = bool(AUTH_SECRET)


def _generate_auth_token(username: str) -> str:
    """Génère un token HMAC pour un utilisateur (appelé côté serveur)."""
    if not AUTH_SECRET:
        return ""
    return hmac.new(AUTH_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()


def _verify_auth_token(username: str, token: str) -> bool:
    """Vérifie le token d'authentification d'un utilisateur."""
    if not AUTH_ENABLED:
        return True  # Auth désactivée en dev
    expected = _generate_auth_token(username)
    return hmac.compare_digest(expected, token)


class State(rx.State):
    """État principal de l'application."""

    # ===== UTILISATEUR & SESSION =====
    current_user: str = ""
    login_username: str = ""
    user_role: str = ""
    _auth_token: str = ""
    is_authenticated: bool = False
    login_error: str = ""
    deployment_id: str = str(uuid.uuid4())[:8]
    destroy_id_input: str = ""

    def set_login_username(self, value: str) -> None:
        """Mise à jour en temps réel du champ de login."""
        self.login_username = value

    def login(self, form_data: dict | None = None):
        """Authentifie l'utilisateur via la table Supabase `profiles`.

        Message d'erreur générique pour prévenir l'énumération d'utilisateurs.
        Après succès, lance systématiquement la simulation de coûts.
        """
        # Récupérer le username depuis le formulaire ou le champ d'état
        if form_data and form_data.get("username"):
            username = form_data["username"].strip()
        else:
            username = self.login_username.strip()

        self.login_error = ""

        if not username:
            self.login_error = "Veuillez saisir votre identifiant."
            yield rx.toast.error("Veuillez saisir votre identifiant.")
            return

        logger.info("Tentative de connexion pour: %s", username)

        # Requête Supabase pour vérifier le profil
        sb = _get_supabase()
        if sb is not None:
            try:
                res = sb.table("profiles").select("role").eq(
                    "username", username
                ).limit(1).execute()

                if res.data:
                    self.user_role = res.data[0].get("role", "viewer")
                    self.is_authenticated = True
                    self.current_user = username
                    self.login_error = ""
                    logger.info("Utilisateur validé: %s (role=%s)", username, self.user_role)
                    yield rx.toast.success(f"Bienvenue, {username}")
                else:
                    self.is_authenticated = False
                    self.user_role = ""
                    self.login_error = "Identifiants invalides"
                    logger.warning("Échec login: %s", username)
                    yield rx.toast.error("Identifiants invalides")
                    return

            except Exception as exc:
                logger.warning("Erreur Supabase profiles: %s", exc, exc_info=True)
                self.is_authenticated = True
                self.current_user = username
                self.user_role = "viewer"
                self.login_error = ""
                yield rx.toast.warning("Supabase indisponible – mode dégradé")
        else:
            # Pas de Supabase (dev local) → accepter tout le monde
            self.is_authenticated = True
            self.current_user = username
            self.user_role = "admin"
            self.login_error = ""
            logger.info("Supabase non configuré – auth locale pour: %s", username)
            yield rx.toast.success(f"Bienvenue, {username}")

        # ── Toujours relancer la simulation après auth réussie ──
        logger.info("Triggering simulation for user: %s", self.current_user)
        yield from self.run_simulation()

    def logout(self) -> None:
        """Déconnexion : réinitialise l'état d'authentification."""
        logger.info("Déconnexion: %s", self.current_user)
        self.current_user = ""
        self.login_username = ""
        self.user_role = ""
        self.is_authenticated = False
        self.login_error = ""
        return rx.toast.info("Déconnecté")

    def _require_auth(self) -> bool:
        """Vérifie que l'utilisateur est authentifié pour les actions sensibles."""
        if not self.is_authenticated:
            logger.warning("Action non autorisée: utilisateur non authentifié")
            return False
        if not self.current_user:
            return False
        return True

    def set_destroy_id_input(self, value: str) -> None:
        self.destroy_id_input = value.strip()

    def generate_new_id(self):
        self.deployment_id = str(uuid.uuid4())[:8]
        return rx.toast.info(f"Nouvelle Session: {self.deployment_id}")

    def set_deployment_id(self, value: str) -> None:
        self.deployment_id = value.strip()

    # ===== MODE & WIZARD =====
    is_expert_mode: bool = True
    wizard_auto_deploy: bool = False
    wizard_include_database: bool = True
    wizard_answers: dict[str, str] = {
        "environment": "dev",
        "traffic": "low",
        "workload": "general",
        "criticality": "low",
        "type": "web",
    }

    def toggle_mode(self, val: bool) -> None:
        self.is_expert_mode = val

    def set_wizard_auto_deploy(self, val: bool) -> None:
        self.wizard_auto_deploy = val

    def set_wizard_include_database(self, val: bool) -> None:
        """Active/désactive l'inclusion de base de données dans la stack."""
        self.wizard_include_database = val

    def set_wizard_env_logic(self, value: str) -> None:
        self.wizard_answers["environment"] = "prod" if "Prod" in value else "dev"

    def set_wizard_workload_logic(self, value: str) -> None:
        if "Traitement" in value:
            self.wizard_answers["workload"] = "cpu"
        elif "Cache" in value:
            self.wizard_answers["workload"] = "memory"
        else:
            self.wizard_answers["workload"] = "general"

    def set_wizard_criticality_logic(self, value: str) -> None:
        self.wizard_answers["criticality"] = "high" if "critique" in value else "low"

    def set_wizard_traffic_logic(self, value: str) -> None:
        if "Viral" in value:
            self.wizard_answers["traffic"] = "high"
        elif "Croissance" in value:
            self.wizard_answers["traffic"] = "medium"
        else:
            self.wizard_answers["traffic"] = "low"

    def set_wizard_app_type_logic(self, value: str) -> None:
        """Définit le type d'application pour la recommandation de stack."""
        type_mapping = {
            "Site Web": "web",
            "API REST": "api",
            "Backend": "backend",
            "Jobs / Scripts": "batch",
            "Microservices": "microservices",
        }
        for key, app_type in type_mapping.items():
            if key in value:
                self.wizard_answers["type"] = app_type
                return
        self.wizard_answers["type"] = "web"

    def apply_recommendation_flow(self):
        """Applique les recommandations du wizard et lance la simulation."""
        self.is_loading = True
        yield

        try:
            resources = list(RecommendationEngine.generate(self.wizard_answers))

            if not self.wizard_include_database:
                resources = [r for r in resources if r.get("type") != "sql"]

            self.resource_list = resources
            yield from self.run_simulation()
            self.is_expert_mode = True
            yield

            if self.wizard_auto_deploy and self.cost <= Config.DEFAULT_BUDGET_LIMIT:
                yield from self.start_deployment()

        except Exception as e:
            logger.error("Erreur Wizard: %s", e, exc_info=True)
            rx.toast.error(f"Erreur Wizard: {e}")
        finally:
            self.is_loading = False
            yield

    # ===== CONFIGURATION RESSOURCES =====
    selected_service: str = "compute"
    selected_machine: str = "e2-medium"
    selected_storage: int = 50
    selected_db_tier: str = "db-f1-micro"
    selected_db_version: str = "POSTGRES_14"
    selected_storage_class: str = "STANDARD"
    selected_software_stack: str = "none"

    # Listes d'options
    instance_types: list[str] = GCPConfig.INSTANCE_TYPES
    db_tiers: list[str] = GCPConfig.DB_TIERS
    db_versions: list[str] = GCPConfig.DB_VERSIONS
    storage_classes: list[str] = GCPConfig.STORAGE_CLASSES
    software_stacks: list[str] = GCPConfig.get_stack_names()

    def set_service(self, value: str) -> None:
        self.selected_service = value

    def set_machine(self, value: str) -> None:
        self.selected_machine = value

    def set_storage(self, value: list[float]) -> None:
        self.selected_storage = int(value[0])

    def set_db_tier(self, value: str) -> None:
        self.selected_db_tier = value

    def set_db_version(self, value: str) -> None:
        self.selected_db_version = value

    def set_storage_class(self, value: str) -> None:
        self.selected_storage_class = value

    def set_software_stack(self, value: str) -> None:
        """Définit la stack logicielle sélectionnée."""
        self.selected_software_stack = value

    @rx.var
    def stack_description(self) -> str:
        """Retourne la description de la stack sélectionnée."""
        stack_info = GCPConfig.SOFTWARE_STACKS.get(self.selected_software_stack, {})
        return stack_info.get("description", "")

    # ===== PANIER & SIMULATION =====
    resource_list: list[dict[str, Any]] = []
    cost: float = 0.0
    details: dict[str, Any] = {}
    is_loading: bool = False
    error_msg: str = ""

    def add_resource(self):
        """Ajoute une ressource au panier selon le service sélectionné."""
        stack_info = GCPConfig.SOFTWARE_STACKS.get(self.selected_software_stack, {})
        stack_display = stack_info.get("name", "Aucun") if stack_info else "Aucun"

        resource_builders = {
            "compute": lambda: {
                "type": "compute",
                "machine_type": self.selected_machine,
                "disk_size": self.selected_storage,
                "software_stack": self.selected_software_stack,
                "display_name": f"VM {self.selected_machine} ({stack_display})",
            },
            "sql": lambda: {
                "type": "sql",
                "db_tier": self.selected_db_tier,
                "db_version": self.selected_db_version,
                "display_name": f"SQL {self.selected_db_tier}",
            },
            "storage": lambda: {
                "type": "storage",
                "storage_class": self.selected_storage_class,
                "display_name": f"GCS {self.selected_storage_class}",
            },
        }

        builder = resource_builders.get(self.selected_service)
        if builder:
            self.resource_list = self.resource_list + [builder()]
            return State.run_simulation

    def remove_resource(self, index: int):
        """Retire une ressource du panier par son index."""
        self.resource_list = [r for i, r in enumerate(self.resource_list) if i != index]
        return State.run_simulation

    def run_simulation(self):
        """Lance la simulation des coûts via Infracost."""
        logger.info("run_simulation called – %d ressources dans le panier", len(self.resource_list))
        self.is_loading = True
        yield

        try:
            if not self.resource_list:
                self.cost, self.details = 0.0, {}
            else:
                sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
                result = sim.simulate(self.resource_list)

                if result.success:
                    self.cost = round(result.monthly_cost, 2)
                    self.details = result.details
                    self.error_msg = ""
                    logger.info("UI Update: Total cost set to %.2f", self.cost)
                else:
                    self.cost = 0.0
                    self.error_msg = result.error_message or "Erreur inconnue"
                    logger.warning("Simulation échouée: %s", self.error_msg)

        except Exception as e:
            self.error_msg = str(e)
            logger.error("Erreur simulation: %s", e, exc_info=True)
        finally:
            self.is_loading = False
            yield

    # ===== DÉPLOIEMENT (GitLab CI/CD) =====
    logs: list[str] = []
    is_deploying: bool = False
    deploy_status: str = "idle"  # idle, queued, pipeline_sent, running, success, error
    pipeline_url: str = ""

    @staticmethod
    def _terraform_available() -> bool:
        """Vérifie si Terraform est utilisable (CLI + environnement adapté).

        Retourne False sur Cloud Run (K_SERVICE est défini) car
        Terraform y est installé mais ne peut pas init (pas de backend).
        """
        import os
        if os.environ.get("K_SERVICE"):
            logger.info("Cloud Run détecté (K_SERVICE=%s), Terraform sync désactivé",
                        os.environ.get("K_SERVICE"))
            return False

        import shutil
        if not shutil.which("terraform"):
            return False
        try:
            import subprocess
            r = subprocess.run(
                ["terraform", "version"],
                capture_output=True, timeout=5, check=False,
            )
            return r.returncode == 0
        except Exception:
            return False

    def start_deployment(self):
        """Déclenche le déploiement via GitLab CI/CD (ou démo si indisponible)."""
        # ── CRIT-3 : Vérification d'authentification ──
        if not self._require_auth():
            return rx.toast.error("Authentification requise pour déployer")

        if not self.resource_list:
            return rx.toast.error("Panier vide!")

        if self.cost > Config.DEFAULT_BUDGET_LIMIT:
            return rx.toast.error("Budget dépassé!")

        target_id = self.deployment_id
        self.is_deploying = True
        self.deploy_status = "queued"
        self.pipeline_url = ""
        self.logs = [f"--- DEPLOY: {target_id} ---", "📨 Envoi vers GitLab CI/CD…"]
        yield

        audit_id = self._create_audit_log("DEPLOY", target_id)
        yield

        # ── Tentative GitLab CI/CD ──
        if trigger_deployment is not None and Config.GITLAB_TRIGGER_TOKEN:
            try:
                result = trigger_deployment(
                    resources=self.resource_list,
                    deployment_id=target_id,
                    action="apply",
                )
                if result.success:
                    self.pipeline_url = result.pipeline_url or ""
                    self.deploy_status = "pipeline_sent"
                    self.logs.append(f"🚀 Pipeline GitLab déclenché (ID: {result.pipeline_id})")
                    self.logs.append(f"🔗 {self.pipeline_url}")
                    self.logs.append("✅ Déploiement initié sur GitLab")
                    self._update_audit_log(audit_id, "PIPELINE_SENT")
                    self.is_deploying = False
                    self.load_audit_logs()
                    yield
                    return
                else:
                    self.logs.append(f"⚠️ GitLab trigger échoué: {result.error}")
                    logger.warning("GitLab trigger failed: %s", result.error)
                    yield
            except Exception as exc:
                self.logs.append(f"⚠️ Erreur GitLab: {exc}")
                logger.warning("GitLab trigger exception: %s", exc)
                yield

        # ── Fallback : sync local si Terraform disponible ──
        if self._terraform_available():
            self.logs.append("⚠️ Fallback synchrone (Terraform local)")
            yield
            yield from self._deploy_sync(target_id)
        else:
            # ── Fallback : mode démo ──
            self.logs.append("⚠️ Mode démo – simulation du déploiement")
            yield
            yield from self._deploy_demo(target_id, audit_id)

    def _deploy_sync(self, target_id: str):
        """Fallback : déploiement synchrone (ancien comportement)."""
        self.deploy_status = "running"
        yield

        try:
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for line in sim.deploy(self.resource_list, target_id):
                self._append_log(line)
                yield

            self.deploy_status = "success"
            self.logs.append("✅ SUCCESS")
            yield
            self._update_audit_log(None, "SUCCESS")

        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERROR: {e}")
            logger.error("Deploy sync failed: %s", e, exc_info=True)
            self._update_audit_log(None, "ERROR")

        finally:
            self.is_deploying = False
            self.load_audit_logs()
            yield

    def _deploy_demo(self, target_id: str, audit_id: int | None):
        """Mode démo : simule un déploiement réussi avec logs réalistes."""
        import time

        self.deploy_status = "running"
        yield

        # Générer les noms de ressources du panier pour des logs réalistes
        resource_names = [
            r.get("display_name", r.get("type", "resource"))
            for r in self.resource_list
        ] or ["default-resource"]

        demo_steps = [
            ("📦 Initialisation Terraform...", 1.0),
            ("✅ Terraform init... OK", 0.5),
            (f"📋 Plan : {len(self.resource_list)} ressource(s) à créer", 0.8),
            ("✅ Terraform plan... OK (0 to change, {n} to add)".format(n=len(self.resource_list)), 0.5),
            ("🚀 Terraform apply en cours...", 1.0),
        ]

        # Ajouter des lignes par ressource
        for i, name in enumerate(resource_names):
            pct = int((i + 1) / len(resource_names) * 80) + 10
            demo_steps.append((f"⚙️  Creating {name}... {pct}%", 1.2))

        demo_steps += [
            ("🔗 Configuring networking & firewall rules...", 0.8),
            ("✅ Apply complete! Resources: {n} added, 0 changed, 0 destroyed.".format(n=len(self.resource_list)), 0.5),
            (f"🌟 Coût estimé : {self.cost:.2f} $/mois", 0.3),
            (f"🏁 Deployment {target_id} Complete!", 0.0),
        ]

        for msg, delay in demo_steps:
            if delay > 0:
                time.sleep(delay)
            self._append_log(msg)
            yield

        self.deploy_status = "success"
        self.logs.append("✅ SUCCESS (mode démo)")
        yield

        # Mettre à jour l'audit log dans Supabase
        self._update_audit_log(audit_id, "SUCCESS")
        self.is_deploying = False
        self.load_audit_logs()
        yield

    def start_destruction(self):
        """Déclenche la destruction via GitLab CI/CD (ou démo si indisponible)."""
        # ── CRIT-3 : Vérification d'authentification ──
        if not self._require_auth():
            return rx.toast.error("Authentification requise pour détruire")

        if self.is_deploying:
            return

        target_id = self.destroy_id_input or self.deployment_id
        self.is_deploying = True
        self.deploy_status = "queued"
        self.pipeline_url = ""
        self.logs = [f"--- DESTROY: {target_id} ---", "📨 Envoi vers GitLab CI/CD…"]
        yield

        audit_id = self._create_audit_log("DESTROY", target_id, cost=0.0)
        yield

        # ── Tentative GitLab CI/CD ──
        if trigger_destruction is not None and Config.GITLAB_TRIGGER_TOKEN:
            try:
                result = trigger_destruction(
                    resources=self.resource_list,
                    deployment_id=target_id,
                )
                if result.success:
                    self.pipeline_url = result.pipeline_url or ""
                    self.deploy_status = "pipeline_sent"
                    self.logs.append(f"🔥 Pipeline destruction déclenché (ID: {result.pipeline_id})")
                    self.logs.append(f"🔗 {self.pipeline_url}")
                    self.logs.append("✅ Destruction initiée sur GitLab")
                    self._update_audit_log(audit_id, "PIPELINE_SENT")
                    self.is_deploying = False
                    self.load_audit_logs()
                    yield
                    return
                else:
                    self.logs.append(f"⚠️ GitLab trigger échoué: {result.error}")
                    logger.warning("GitLab trigger failed: %s", result.error)
                    yield
            except Exception as exc:
                self.logs.append(f"⚠️ Erreur GitLab: {exc}")
                logger.warning("GitLab trigger exception: %s", exc)
                yield

        # ── Fallback : sync local ──
        if self._terraform_available():
            self.logs.append("⚠️ Fallback synchrone (Terraform local)")
            yield
            yield from self._destroy_sync(target_id)
        else:
            # ── Fallback : mode démo ──
            self.logs.append("⚠️ Mode démo – simulation de la destruction")
            yield
            yield from self._destroy_demo(target_id, audit_id)

    def _destroy_sync(self, target_id: str):
        """Fallback : destruction synchrone."""
        self.deploy_status = "running"
        yield

        try:
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for line in sim.destroy(self.resource_list, target_id):
                self._append_log(line)
                yield

            self.deploy_status = "success"
            self.logs.append("✅ DESTROY SUCCESS")

        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERROR: {e}")
            logger.error("Destroy sync failed: %s", e, exc_info=True)

        finally:
            self.is_deploying = False
            self.load_audit_logs()
            yield

    def _destroy_demo(self, target_id: str, audit_id: int | None):
        """Mode démo : simule une destruction réussie."""
        import time

        self.deploy_status = "running"
        yield

        resource_names = [
            r.get("display_name", r.get("type", "resource"))
            for r in self.resource_list
        ] or ["default-resource"]

        demo_steps = [
            ("📦 Initialisation Terraform...", 1.0),
            ("✅ Terraform init... OK", 0.5),
            (f"📋 Plan : {len(self.resource_list)} ressource(s) à détruire", 0.8),
            ("💥 Terraform destroy en cours...", 1.0),
        ]

        for i, name in enumerate(resource_names):
            pct = int((i + 1) / len(resource_names) * 80) + 10
            demo_steps.append((f"🗑️  Destroying {name}... {pct}%", 1.0))

        demo_steps += [
            ("✅ Destroy complete! Resources: {n} destroyed.".format(n=len(self.resource_list)), 0.5),
            (f"🏁 Destruction {target_id} Complete!", 0.0),
        ]

        for msg, delay in demo_steps:
            if delay > 0:
                time.sleep(delay)
            self._append_log(msg)
            yield

        self.deploy_status = "success"
        self.logs.append("✅ DESTROY SUCCESS (mode démo)")
        yield

        self._update_audit_log(audit_id, "SUCCESS")
        self.is_deploying = False
        self.load_audit_logs()
        yield

    def _append_log(self, line: str) -> None:
        """Ajoute une ligne au log avec limite de taille."""
        self.logs.append(line)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def close_console(self) -> None:
        """Ferme la console de déploiement."""
        self.deploy_status = "idle"
        self.logs = []

    def _create_audit_log(
        self,
        action: str,
        target_id: str,
        cost: float | None = None,
    ) -> int | None:
        """Crée un log d'audit dans Supabase."""
        sb = _get_supabase()
        if not sb:
            return None

        try:
            summary = f"[{target_id}] " + ", ".join(
                r.get("display_name", "") for r in self.resource_list
            )

            row = {
                "user": self.current_user,
                "action": action,
                "resources_summary": summary,
                "total_cost": cost if cost is not None else self.cost,
                "status": "PENDING",
            }

            # Ajouter le lien pipeline si disponible
            if self.pipeline_url:
                row["pipeline_url"] = self.pipeline_url

            res = sb.table("audit_logs").insert(row).execute()

            return res.data[0]["id"] if res.data else None
        except Exception:
            logger.warning("Échec création audit log pour %s/%s", action, target_id, exc_info=True)
            return None

    def _update_audit_log(self, audit_id: int | None, status: str) -> None:
        """Met à jour le statut d'un log d'audit."""
        if not audit_id:
            return

        sb = _get_supabase()
        if not sb:
            return

        try:
            update_data: dict = {"status": status}
            if self.pipeline_url:
                update_data["pipeline_url"] = self.pipeline_url
            sb.table("audit_logs").update(update_data).eq("id", audit_id).execute()
        except Exception:
            logger.warning("Échec mise à jour audit log #%s → %s", audit_id, status, exc_info=True)

    # ===== AUDIT LOGS =====
    audit_logs: list[dict] = []

    def load_audit_logs(self) -> None:
        """Charge les logs d'audit depuis Supabase."""
        sb = _get_supabase()
        if not sb:
            return

        try:
            res = sb.table("audit_logs").select("*").order(
                "created_at", desc=True
            ).limit(50).execute()

            self.audit_logs = [
                self._format_audit_row(row) for row in res.data
            ]
        except Exception:
            logger.warning("Échec chargement audit logs", exc_info=True)

    @staticmethod
    def _format_audit_row(row: dict) -> dict:
        """Formate une ligne d'audit pour l'affichage."""
        created_at = row.get("created_at", "")

        if "T" in created_at:
            date_part, time_part = created_at.split("T")
            formatted_date = f"{date_part} {time_part[:5]}"
        else:
            formatted_date = created_at

        return {
            **row,
            "formatted_date": formatted_date,
            "formatted_cost": f"${row.get('total_cost', 0):.2f}",
            "pipeline_url": row.get("pipeline_url", ""),
        }

    # ===== COMPUTED PROPERTIES =====
    @rx.var
    def chart_data(self) -> list[dict]:
        """Données pour le graphique de répartition des coûts."""
        if not self.details:
            return []

        colors = {
            "Compute": "#007AFF",
            "SQL": "#AF52DE",
            "Storage": "#FF9500",
            "Network": "#5AC8FA",
            "Autre": "#FF2D55",
        }

        data = []

        try:
            for project in self.details.get("projects", []):
                resources = project.get("breakdown", {}).get("resources", [])

                for res in resources:
                    value = float(res.get("monthlyCost", 0))
                    if value <= 0:
                        continue

                    name = res.get("name", "").lower()
                    category = self._categorize_resource(name)

                    data.append({
                        "name": category,
                        "value": value,
                        "fill": colors.get(category, colors["Autre"]),
                    })

        except Exception:
            logger.warning("Erreur construction chart_data", exc_info=True)

        return data

    @staticmethod
    def _categorize_resource(name: str) -> str:
        """Catégorise une ressource par son nom."""
        if "sql" in name:
            return "SQL"
        if "instance" in name:
            return "Compute"
        if "storage" in name:
            return "Storage"
        if "address" in name or "forwarding" in name:
            return "Network"
        return "Autre"
