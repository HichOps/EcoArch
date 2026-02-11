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
    """Page principale – verrouillée derrière l'écran de login."""
    return rx.box(
        rx.html(f"<style>{GLOBAL_ANIMATIONS}</style>"),
        rx.cond(
            State.is_authenticated,
            _authenticated_app(),
            _login_screen(),
        ),
        background=rx.color("gray", 1),
        min_height="100vh",
        font_family="'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
    )


def _login_screen() -> rx.Component:
    """Écran de connexion centré – aucune info utilisateur exposée."""
    return rx.center(
        rx.vstack(
            # Logo
            rx.center(
                rx.box(
                    rx.icon("shield-check", size=32, color="white"),
                    background="linear-gradient(135deg, var(--accent-9), var(--accent-11))",
                    padding="16px",
                    border_radius="20px",
                    box_shadow="0 8px 32px rgba(0, 122, 255, 0.3)",
                ),
                width="100%",
            ),
            rx.heading(
                "EcoArch",
                size="7",
                weight="bold",
                letter_spacing="-0.03em",
                text_align="center",
            ),
            rx.text(
                "Architecture Cloud Responsable",
                size="3",
                color="var(--gray-10)",
                text_align="center",
            ),
            # Formulaire de login
            rx.el.form(
                rx.vstack(
                    rx.input(
                        placeholder="Identifiant",
                        name="username",
                        value=State.login_username,
                        on_change=State.set_login_username,
                        size="3",
                        variant="surface",
                        radius="large",
                        width="100%",
                        auto_focus=True,
                    ),
                    rx.cond(
                        State.login_error != "",
                        rx.text(
                            State.login_error,
                            color="var(--red-11)",
                            size="2",
                            text_align="center",
                        ),
                        rx.fragment(),
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("log-in", size=16),
                            rx.text("Accéder"),
                            spacing="2",
                            align="center",
                        ),
                        type="submit",
                        size="3",
                        width="100%",
                        radius="large",
                        cursor="pointer",
                    ),
                    spacing="4",
                    width="100%",
                ),
                on_submit=State.login,
                reset_on_submit=False,
                width="100%",
            ),
            spacing="5",
            width="340px",
            padding="40px",
            background="white",
            border_radius="24px",
            border="1px solid var(--gray-4)",
            box_shadow="0 20px 60px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04)",
            align="center",
        ),
        min_height="100vh",
    )


def _authenticated_app() -> rx.Component:
    """Application complète visible après authentification."""
    return rx.box(
        user_topbar(),
        header(),
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon("layers", size=16),
                            rx.text("Architect Builder"),
                            spacing="2",
                            align="center",
                        ),
                        value="sim",
                    ),
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon("scroll-text", size=16),
                            rx.text("Journal d'Audit"),
                            spacing="2",
                            align="center",
                        ),
                        value="gov",
                    ),
                    size="2",
                    justify="center",
                ),
                
                # Onglet Builder
                rx.tabs.content(
                    _builder_tab(),
                    value="sim",
                    padding_top="2.5rem",
                ),
                
                # Onglet Audit
                rx.tabs.content(
                    governance_dashboard(),
                    value="gov",
                    padding_top="2.5rem",
                ),
                
                default_value="sim",
                width="100%",
            ),
            size="3",
            padding_y="1rem",
        ),
        on_mount=State.run_simulation,
    )


def _builder_tab() -> rx.Component:
    """Contenu de l'onglet Builder."""
    return rx.vstack(
        # Toggle Expert/Assistant avec design Apple
        rx.center(
            rx.box(
                rx.hstack(
                    rx.text(
                        "Assistant",
                        weight="medium",
                        size="2",
                        color=rx.cond(
                            ~State.is_expert_mode,
                            "var(--accent-11)",
                            "var(--gray-10)",
                        ),
                        letter_spacing="-0.01em",
                    ),
                    rx.switch(
                        checked=State.is_expert_mode,
                        on_change=State.toggle_mode,
                        color_scheme="blue",
                        size="2",
                        cursor="pointer",
                    ),
                    rx.text(
                        "Expert",
                        weight="medium",
                        size="2",
                        color=rx.cond(
                            State.is_expert_mode,
                            "var(--accent-11)",
                            "var(--gray-10)",
                        ),
                        letter_spacing="-0.01em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                padding="12px 24px",
                border_radius="var(--radius-full)",
                background="var(--gray-2)",
                border="1px solid var(--gray-4)",
                box_shadow="0 2px 8px rgba(0, 0, 0, 0.04)",
                transition="all 0.2s ease",
                _hover={
                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.08)",
                },
            ),
            width="100%",
            margin_bottom="24px",
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
                rx.box(
                    rx.callout.root(
                        rx.callout.icon(rx.icon("triangle-alert")),
                        rx.callout.text(State.error_msg),
                        color_scheme="red",
                        role="alert",
                        width="100%",
                    ),
                    class_name="animate-in",
                ),
            ),
            pricing_block(),
            rx.cond(
                State.is_loading,
                rx.center(
                    rx.spinner(size="3", color="var(--accent-9)"),
                    width="100%",
                    padding="2rem",
                ),
            ),
            width="100%",
            spacing="6",
        ),
        columns="2",
        spacing="6",
        width="100%",
    )


# Configuration de l'application
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue",
        gray_color="slate",
        radius="large",
        scaling="100%",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ],
)

# Enregistrement de la page avec chargement initial des logs
app.add_page(
    index,
    title="EcoArch",
    on_load=[State.load_audit_logs, State.start_audit_polling],
)