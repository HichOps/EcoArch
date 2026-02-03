"""Point d'entrée principal de l'application EcoArch."""
import reflex as rx

from .state import State
from .styles import GLOBAL_ANIMATIONS
from .components.header import header
from .components.topbar import user_topbar
from .components.form import configuration_form
from .components.resources import resource_list_display
from .components.pricing import pricing_block
from .components.stats import governance_dashboard
from .components.logs import deploy_console
from .components.wizard import wizard_block


def index() -> rx.Component:
    """Page principale de l'application."""
    return rx.box(
        rx.html(f"<style>{GLOBAL_ANIMATIONS}</style>"),
        user_topbar(),
        header(),
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Architect Builder", value="sim"),
                    rx.tabs.trigger("Journal d'Audit", value="gov"),
                    size="2",
                ),
                
                # Onglet Builder
                rx.tabs.content(
                    _builder_tab(),
                    value="sim",
                    padding_top="2rem",
                ),
                
                # Onglet Audit
                rx.tabs.content(
                    governance_dashboard(),
                    value="gov",
                    padding_top="2rem",
                ),
                
                default_value="sim",
                width="100%",
            ),
            size="2",
        ),
        background=rx.color("slate", 1),
        min_height="100vh",
        font_family="Inter",
    )


def _builder_tab() -> rx.Component:
    """Contenu de l'onglet Builder."""
    return rx.vstack(
        # Toggle Expert/Assistant
        rx.center(
            rx.hstack(
                rx.text(
                    "Assistant",
                    weight="bold",
                    color=rx.cond(
                        ~State.is_expert_mode,
                        "var(--violet-9)",
                        "var(--gray-9)",
                    ),
                ),
                rx.switch(
                    checked=State.is_expert_mode,
                    on_change=State.toggle_mode,
                    color_scheme="violet",
                    size="3",
                    cursor="pointer",
                ),
                rx.text(
                    "Expert",
                    weight="bold",
                    color=rx.cond(
                        State.is_expert_mode,
                        "var(--violet-9)",
                        "var(--gray-9)",
                    ),
                ),
                spacing="4",
                padding="10px",
                border="1px solid var(--gray-4)",
                border_radius="full",
                margin_bottom="20px",
                align_items="center",
                background="white",
            ),
            width="100%",
        ),
        
        # Contenu conditionnel
        rx.cond(
            State.is_expert_mode,
            _expert_mode_content(),
            rx.center(wizard_block(), width="100%", padding_y="20px"),
        ),
        
        deploy_console(),
        width="100%",
        spacing="6",
    )


def _expert_mode_content() -> rx.Component:
    """Contenu du mode expert."""
    return rx.grid(
        configuration_form(),
        rx.vstack(
            resource_list_display(),
            rx.cond(
                State.error_msg != "",
                rx.callout.root(
                    rx.callout.icon(rx.icon("triangle-alert")),
                    rx.callout.text(State.error_msg),
                    color_scheme="ruby",
                    role="alert",
                    width="100%",
                ),
            ),
            pricing_block(),
            rx.cond(
                State.is_loading,
                rx.center(rx.spinner(size="3"), width="100%", padding="2rem"),
            ),
            width="100%",
            spacing="6",
        ),
        columns="2",
        spacing="8",
        width="100%",
    )


# Configuration de l'application
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="indigo",
        radius="large",
    ),
)

# Enregistrement de la page avec chargement initial des logs
app.add_page(index, title="EcoArch V10", on_load=State.load_audit_logs)