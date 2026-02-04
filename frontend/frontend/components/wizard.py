"""Composant Wizard assistant de configuration - Design Apple-like."""
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
    """Assistant de configuration guidée avec design Apple."""
    return rx.center(
        rx.vstack(
            # En-tête avec icône stylisée
            rx.box(
                rx.icon("sparkles", size=28, color="white"),
                background="linear-gradient(135deg, #007AFF 0%, #5856D6 100%)",
                padding="16px",
                border_radius="20px",
                box_shadow="0 8px 24px rgba(0, 122, 255, 0.3)",
            ),
            rx.heading(
                "Assistant Développeur",
                size="6",
                weight="bold",
                letter_spacing="-0.03em",
                margin_top="16px",
            ),
            rx.text(
                "Décrivez votre projet, je m'occupe des serveurs.",
                color="var(--gray-10)",
                size="3",
                weight="medium",
            ),
            
            rx.box(height="24px"),
            
            # Questions avec design épuré
            _wizard_question(
                "1",
                "À quelle étape est votre projet ?",
                WIZARD_OPTIONS["env"],
                State.set_wizard_env_logic,
                direction="row",
            ),
            
            _wizard_question(
                "2",
                "Quel type d'application développez-vous ?",
                WIZARD_OPTIONS["app_type"],
                State.set_wizard_app_type_logic,
                direction="column",
            ),
            
            _wizard_question(
                "3",
                "Que fait votre code principalement ?",
                WIZARD_OPTIONS["workload"],
                State.set_wizard_workload_logic,
                direction="column",
            ),
            
            _wizard_question(
                "4",
                "Si le serveur plante à 3h du matin...",
                WIZARD_OPTIONS["criticality"],
                State.set_wizard_criticality_logic,
                direction="column",
            ),
            
            _wizard_question(
                "5",
                "Combien d'utilisateurs visez-vous ?",
                WIZARD_OPTIONS["traffic"],
                State.set_wizard_traffic_logic,
                direction="row",
            ),
            
            rx.box(height="24px"),
            
            # Options avancées
            rx.vstack(
                _include_database_option(),
                _auto_deploy_option(),
                spacing="3",
                width="100%",
            ),
            
            # Bouton générer avec style Apple
            rx.button(
                rx.hstack(
                    rx.icon("sparkles", size=18),
                    rx.text("Générer ma Stack", weight="bold"),
                    spacing="2",
                    align="center",
                ),
                on_click=State.apply_recommendation_flow,
                size="4",
                width="100%",
                variant="solid",
                cursor="pointer",
                margin_top="16px",
                radius="large",
                _active={"transform": "scale(0.98)"},
                transition="all 0.15s ease",
            ),
        ),
        padding="40px",
        border="1px solid var(--gray-4)",
        border_radius="24px",
        background="var(--gray-1)",
        box_shadow="0 4px 16px rgba(0, 0, 0, 0.06)",
        width="100%",
        max_width="680px",
        class_name="animate-in",
    )


def _wizard_question(
    number: str,
    label: str,
    options: list[str],
    on_change,
    direction: str = "column",
) -> rx.Component:
    """Question du wizard avec design Apple."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.text(
                        number,
                        weight="bold",
                        size="1",
                        color="var(--accent-11)",
                    ),
                    background="var(--accent-3)",
                    width="24px",
                    height="24px",
                    border_radius="8px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(
                    label,
                    weight="bold",
                    size="2",
                    color="var(--gray-12)",
                    letter_spacing="-0.01em",
                ),
                spacing="3",
                align="center",
            ),
            rx.box(
                rx.radio(
                    options,
                    default_value=options[0],
                    on_change=on_change,
                    direction=direction,
                    spacing="3" if direction == "row" else "2",
                    size="2",
                ),
                padding_left="36px",
                padding_top="8px",
            ),
            align="start",
            width="100%",
        ),
        padding="16px 0",
        border_bottom="1px solid var(--gray-4)",
        width="100%",
    )


def _auto_deploy_option() -> rx.Component:
    """Option d'auto-déploiement avec style Apple."""
    return rx.box(
        rx.hstack(
            rx.checkbox(
                on_change=State.set_wizard_auto_deploy,
                size="2",
            ),
            rx.vstack(
                rx.text(
                    "Déployer automatiquement",
                    weight="bold",
                    size="2",
                    color="var(--gray-12)",
                ),
                rx.text(
                    "Si le budget est respecté (< 50$)",
                    size="1",
                    color="var(--gray-10)",
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        padding="16px 20px",
        border="1px solid var(--accent-6)",
        border_radius="14px",
        width="100%",
        background="var(--accent-2)",
        cursor="pointer",
        transition="all 0.2s ease",
        _hover={
            "background": "var(--accent-3)",
        },
    )


def _include_database_option() -> rx.Component:
    """Option pour inclure/exclure la base de données avec style Apple."""
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=State.wizard_include_database,
                on_change=State.set_wizard_include_database,
                size="2",
            ),
            rx.vstack(
                rx.text(
                    "Inclure une base de données",
                    weight="bold",
                    size="2",
                    color="var(--gray-12)",
                ),
                rx.text(
                    "Cloud SQL PostgreSQL (≈ $16/mois)",
                    size="1",
                    color="var(--gray-10)",
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        padding="16px 20px",
        border="1px solid var(--gray-5)",
        border_radius="14px",
        width="100%",
        background="var(--gray-2)",
        cursor="pointer",
        transition="all 0.2s ease",
        _hover={
            "background": "var(--gray-3)",
        },
    )