"""Composant Wizard assistant de configuration."""
import reflex as rx

from ..state import State


# Options du wizard
WIZARD_OPTIONS = {
    "env": [
        "Prototypage / Test (Dev)",
        "Lancement Public (Prod)",
    ],
    "app_type": [
        "Site Web (Frontend + Backend)",
        "API REST / GraphQL",
        "Backend Métier (Django, Flask)",
        "Jobs / Scripts (Batch)",
        "Microservices (Docker)",
    ],
    "workload": [
        "API / Site Web standard (CRUD)",
        "Traitement lourd (Vidéo, IA, Maths)",
        "Gros Cache / In-Memory (Redis, Big Data)",
    ],
    "criticality": [
        "Ce n'est pas grave, il redémarrera.",
        "C'est critique, on perd de l'argent/users.",
    ],
    "traffic": [
        "Juste l'équipe / Bêta (< 1k)",
        "Croissance (10k+)",
        "Viral / Publicité TV (Massif)",
    ],
}


def wizard_block() -> rx.Component:
    """Assistant de configuration guidée."""
    return rx.center(
        rx.vstack(
            # En-tête
            rx.icon("bot", size=48, color="var(--violet-9)"),
            rx.heading("Assistant Développeur", size="6"),
            rx.text(
                "Décrivez votre projet, je m'occupe des serveurs.",
                opacity=0.7,
            ),
            
            rx.divider(margin_y="20px", width="100%"),
            
            # Questions
            _wizard_question(
                "1. À quelle étape est votre projet ?",
                WIZARD_OPTIONS["env"],
                State.set_wizard_env_logic,
                direction="row",
            ),
            
            rx.divider(margin_y="15px", opacity="0.3"),
            
            _wizard_question(
                "2. Quel type d'application développez-vous ?",
                WIZARD_OPTIONS["app_type"],
                State.set_wizard_app_type_logic,
                direction="column",
            ),
            
            rx.divider(margin_y="15px", opacity="0.3"),
            
            _wizard_question(
                "3. Que fait votre code principalement ?",
                WIZARD_OPTIONS["workload"],
                State.set_wizard_workload_logic,
                direction="column",
            ),
            
            rx.divider(margin_y="15px", opacity="0.3"),
            
            _wizard_question(
                "4. Si le serveur plante à 3h du matin...",
                WIZARD_OPTIONS["criticality"],
                State.set_wizard_criticality_logic,
                direction="column",
            ),
            
            rx.divider(margin_y="15px", opacity="0.3"),
            
            _wizard_question(
                "5. Combien d'utilisateurs visez-vous ?",
                WIZARD_OPTIONS["traffic"],
                State.set_wizard_traffic_logic,
                direction="row",
            ),
            
            rx.divider(margin_y="20px", width="100%"),
            
            # Option auto-deploy
            _auto_deploy_option(),
            
            # Bouton générer
            rx.button(
                rx.hstack(
                    rx.icon("sparkles", size=18),
                    rx.text("GÉNÉRER MA STACK"),
                ),
                on_click=State.apply_recommendation_flow,
                size="4",
                width="100%",
                color_scheme="violet",
                variant="solid",
                cursor="pointer",
                margin_top="15px",
            ),
        ),
        padding="40px",
        border="1px solid rgba(255,255,255,0.1)",
        border_radius="16px",
        background="var(--gray-2)",
        width="100%",
        max_width="700px",
    )


def _wizard_question(
    label: str,
    options: list[str],
    on_change,
    direction: str = "column",
) -> rx.Component:
    """Question du wizard avec options radio."""
    return rx.vstack(
        rx.text(label, weight="bold"),
        rx.radio(
            options,
            default_value=options[0],
            on_change=on_change,
            direction=direction,
            spacing="4" if direction == "row" else "2",
        ),
        align="start",
        width="100%",
    )


def _auto_deploy_option() -> rx.Component:
    """Option d'auto-déploiement."""
    return rx.box(
        rx.checkbox(
            "Déployer automatiquement si le budget est respecté (<50$)",
            on_change=State.set_wizard_auto_deploy,
            color_scheme="violet",
        ),
        padding="10px",
        border="1px dashed var(--violet-6)",
        border_radius="8px",
        width="100%",
        background="var(--violet-2)",
    )