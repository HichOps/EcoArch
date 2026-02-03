"""Composant Formulaire de configuration des ressources."""
import reflex as rx

from ..state import State


def configuration_form() -> rx.Component:
    """Formulaire de configuration des ressources GCP."""
    return rx.box(
        rx.vstack(
            rx.heading("Configuration", size="4", weight="bold"),
            rx.box(
                rx.vstack(
                    # Sélection du service
                    _labeled_field("Type de Service"),
                    rx.select(
                        ["compute", "sql", "storage"],
                        value=State.selected_service,
                        on_change=State.set_service,
                        width="100%",
                        variant="soft",
                    ),
                    rx.divider(margin_y="1rem"),
                    
                    # Champs dynamiques selon le service
                    rx.cond(
                        State.selected_service == "compute",
                        _compute_fields(),
                    ),
                    rx.cond(
                        State.selected_service == "sql",
                        _sql_fields(),
                    ),
                    rx.cond(
                        State.selected_service == "storage",
                        _storage_fields(),
                    ),
                    
                    # Bouton d'ajout
                    rx.button(
                        rx.hstack(
                            rx.text("Ajouter Ressource"),
                            rx.icon("plus", size=16),
                        ),
                        on_click=State.add_resource,
                        size="3",
                        width="100%",
                        margin_top="2rem",
                        variant="solid",
                        color_scheme="indigo",
                        cursor="pointer",
                    ),
                    align="start",
                    width="100%",
                    padding="24px",
                ),
                background=rx.color("slate", 2),
                border=f"1px solid {rx.color('slate', 4)}",
                border_radius="12px",
                box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                width="100%",
            ),
            width="100%",
        ),
    )


def _labeled_field(label: str) -> rx.Component:
    """Label de champ réutilisable."""
    return rx.text(
        label,
        size="2",
        weight="bold",
        color=rx.color("slate", 10),
    )


def _compute_fields() -> rx.Component:
    """Champs spécifiques au service Compute."""
    return rx.vstack(
        _labeled_field("Machine"),
        rx.select(
            State.instance_types,
            value=State.selected_machine,
            on_change=State.set_machine,
            width="100%",
        ),
        rx.hstack(
            _labeled_field("Disque (GB)"),
            rx.spacer(),
            rx.badge(f"{State.selected_storage} GB", variant="soft"),
            width="100%",
            margin_top="1rem",
        ),
        rx.slider(
            default_value=[50],
            min=10,
            max=1000,
            on_change=State.set_storage,
            width="100%",
        ),
        rx.divider(margin_y="1rem"),
        _labeled_field("Stack Logicielle"),
        rx.text(
            "Logiciels pré-installés au démarrage",
            size="1",
            color=rx.color("slate", 9),
            margin_bottom="0.5rem",
        ),
        rx.select(
            State.software_stacks,
            value=State.selected_software_stack,
            on_change=State.set_software_stack,
            width="100%",
        ),
        _stack_description(),
        width="100%",
    )


def _stack_description() -> rx.Component:
    """Affiche la description de la stack sélectionnée."""
    return rx.box(
        rx.cond(
            State.selected_software_stack != "none",
            rx.hstack(
                rx.icon("info", size=14, color=rx.color("blue", 9)),
                rx.text(
                    State.stack_description,
                    size="1",
                    color=rx.color("slate", 10),
                ),
                spacing="2",
                align="center",
            ),
            rx.fragment(),
        ),
        margin_top="0.5rem",
    )


def _sql_fields() -> rx.Component:
    """Champs spécifiques au service SQL."""
    return rx.vstack(
        _labeled_field("Tier"),
        rx.select(
            State.db_tiers,
            value=State.selected_db_tier,
            on_change=State.set_db_tier,
            width="100%",
        ),
        _labeled_field("Version"),
        rx.select(
            State.db_versions,
            value=State.selected_db_version,
            on_change=State.set_db_version,
            width="100%",
        ),
        width="100%",
        spacing="2",
    )


def _storage_fields() -> rx.Component:
    """Champs spécifiques au service Storage."""
    return rx.vstack(
        _labeled_field("Classe"),
        rx.select(
            State.storage_classes,
            value=State.selected_storage_class,
            on_change=State.set_storage_class,
            width="100%",
        ),
        width="100%",
    )