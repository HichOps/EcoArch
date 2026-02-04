"""Composant Formulaire de configuration des ressources - Design Apple-like."""
import reflex as rx

from ..state import State


def configuration_form() -> rx.Component:
    """Formulaire de configuration des ressources GCP avec design Apple."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("settings-2", size=16, color="var(--accent-11)"),
                    background="var(--accent-3)",
                    padding="8px",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.heading(
                    "Configuration",
                    size="4",
                    weight="bold",
                    letter_spacing="-0.02em",
                ),
                spacing="3",
                align="center",
            ),
            rx.box(
                rx.vstack(
                    # Sélection du service
                    _labeled_field("Type de Service", "cloud"),
                    rx.select(
                        ["compute", "sql", "storage"],
                        value=State.selected_service,
                        on_change=State.set_service,
                        width="100%",
                        variant="surface",
                        radius="large",
                        size="3",
                    ),
                    rx.box(height="16px"),
                    
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
                    
                    # Bouton d'ajout avec style Apple
                    rx.button(
                        rx.hstack(
                            rx.icon("plus", size=16),
                            rx.text("Ajouter au panier", weight="bold"),
                            spacing="2",
                            align="center",
                        ),
                        on_click=State.add_resource,
                        size="3",
                        width="100%",
                        margin_top="24px",
                        variant="solid",
                        radius="large",
                        cursor="pointer",
                        _active={"transform": "scale(0.98)"},
                        transition="all 0.15s ease",
                    ),
                    align="start",
                    width="100%",
                    padding="24px",
                ),
                background="var(--gray-2)",
                border="1px solid var(--gray-4)",
                border_radius="16px",
                box_shadow="0 2px 8px rgba(0, 0, 0, 0.04)",
                width="100%",
            ),
            width="100%",
            spacing="4",
        ),
    )


def _labeled_field(label: str, icon_name: str = None) -> rx.Component:
    """Label de champ réutilisable avec style Apple."""
    if icon_name:
        return rx.hstack(
            rx.icon(icon_name, size=14, color="var(--gray-10)"),
            rx.text(
                label,
                size="2",
                weight="medium",
                color="var(--gray-11)",
                letter_spacing="-0.01em",
            ),
            spacing="2",
            align="center",
            margin_bottom="6px",
        )
    return rx.text(
        label,
        size="2",
        weight="medium",
        color="var(--gray-11)",
        letter_spacing="-0.01em",
        margin_bottom="6px",
    )


def _compute_fields() -> rx.Component:
    """Champs spécifiques au service Compute."""
    return rx.vstack(
        _labeled_field("Machine", "cpu"),
        rx.select(
            State.instance_types,
            value=State.selected_machine,
            on_change=State.set_machine,
            width="100%",
            variant="surface",
            radius="large",
            size="3",
        ),
        rx.box(height="16px"),
        rx.hstack(
            _labeled_field("Stockage", "hard-drive"),
            rx.spacer(),
            rx.box(
                rx.text(
                    f"{State.selected_storage} GB",
                    weight="bold",
                    size="2",
                    color="var(--accent-11)",
                ),
                background="var(--accent-3)",
                padding="4px 12px",
                border_radius="var(--radius-full)",
            ),
            width="100%",
        ),
        rx.slider(
            default_value=[50],
            min=10,
            max=1000,
            on_change=State.set_storage,
            width="100%",
            size="2",
        ),
        rx.box(height="16px"),
        _labeled_field("Stack Logicielle", "package"),
        rx.text(
            "Logiciels pré-installés au démarrage",
            size="1",
            color="var(--gray-9)",
            margin_bottom="8px",
        ),
        rx.select(
            State.software_stacks,
            value=State.selected_software_stack,
            on_change=State.set_software_stack,
            width="100%",
            variant="surface",
            radius="large",
            size="3",
        ),
        _stack_description(),
        width="100%",
    )


def _stack_description() -> rx.Component:
    """Affiche la description de la stack sélectionnée."""
    return rx.box(
        rx.cond(
            State.selected_software_stack != "none",
            rx.box(
                rx.hstack(
                    rx.icon("info", size=14, color="var(--accent-9)"),
                    rx.text(
                        State.stack_description,
                        size="1",
                        color="var(--gray-11)",
                    ),
                    spacing="2",
                    align="center",
                ),
                padding="10px 12px",
                background="var(--accent-2)",
                border_radius="10px",
                border="1px solid var(--accent-4)",
            ),
            rx.fragment(),
        ),
        margin_top="8px",
    )


def _sql_fields() -> rx.Component:
    """Champs spécifiques au service SQL."""
    return rx.vstack(
        _labeled_field("Tier", "database"),
        rx.select(
            State.db_tiers,
            value=State.selected_db_tier,
            on_change=State.set_db_tier,
            width="100%",
            variant="surface",
            radius="large",
            size="3",
        ),
        rx.box(height="16px"),
        _labeled_field("Version", "git-branch"),
        rx.select(
            State.db_versions,
            value=State.selected_db_version,
            on_change=State.set_db_version,
            width="100%",
            variant="surface",
            radius="large",
            size="3",
        ),
        width="100%",
    )


def _storage_fields() -> rx.Component:
    """Champs spécifiques au service Storage."""
    return rx.vstack(
        _labeled_field("Classe de stockage", "folder"),
        rx.select(
            State.storage_classes,
            value=State.selected_storage_class,
            on_change=State.set_storage_class,
            width="100%",
            variant="surface",
            radius="large",
            size="3",
        ),
        width="100%",
    )