"""Composant Console de déploiement - Design Apple-like."""
import reflex as rx

from ..state import State

# Couleurs terminal Apple
TERMINAL_GREEN = "#32D74B"
TERMINAL_BG = "#1D1D1F"


def log_line(line: str) -> rx.Component:
    """Affiche une ligne de log avec style terminal Apple."""
    return rx.text(
        line,
        font_family="'SF Mono', 'Fira Code', 'Menlo', monospace",
        font_size="13px",
        color=TERMINAL_GREEN,
        line_height="1.6",
    )


def deploy_console() -> rx.Component:
    """Console de déploiement affichée pendant les opérations - Style Apple."""
    # Afficher la console si en déploiement OU si des logs existent (pour voir le résultat)
    return rx.cond(
        State.is_deploying | (State.deploy_status != "idle"),
        rx.box(
            rx.vstack(
                # En-tête style macOS
                rx.hstack(
                    # Traffic lights
                    rx.hstack(
                        rx.box(
                            width="12px",
                            height="12px",
                            border_radius="50%",
                            background="#FF5F56",
                        ),
                        rx.box(
                            width="12px",
                            height="12px",
                            border_radius="50%",
                            background="#FFBD2E",
                        ),
                        rx.box(
                            width="12px",
                            height="12px",
                            border_radius="50%",
                            background="#27C93F",
                        ),
                        spacing="2",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.cond(
                            State.deploy_status == "running",
                            rx.spinner(color=TERMINAL_GREEN, size="1"),
                            rx.cond(
                                State.deploy_status == "success",
                                rx.icon("circle-check", color=TERMINAL_GREEN, size=14),
                                rx.icon("circle-alert", color="#FF453A", size=14),
                            ),
                        ),
                        rx.text(
                            rx.cond(
                                State.deploy_status == "running",
                                "Déploiement en cours...",
                                rx.cond(
                                    State.deploy_status == "success",
                                    "Terminé avec succès",
                                    "Erreur",
                                ),
                            ),
                            weight="medium",
                            color="var(--gray-11)",
                            size="1",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.spacer(),
                    # Bouton fermer (visible seulement quand terminé)
                    rx.cond(
                        ~State.is_deploying,
                        rx.icon_button(
                            rx.icon("x", size=14),
                            on_click=State.close_console,
                            variant="ghost",
                            size="1",
                            cursor="pointer",
                            color_scheme="gray",
                        ),
                        rx.box(width="28px"),  # Spacer for balance
                    ),
                    width="100%",
                    padding="12px 16px",
                    background="rgba(255, 255, 255, 0.05)",
                    border_bottom="1px solid rgba(255, 255, 255, 0.1)",
                ),
                # Zone de logs scrollable
                rx.scroll_area(
                    rx.box(
                        rx.vstack(
                            rx.foreach(State.logs, log_line),
                            align="start",
                            spacing="1",
                            width="100%",
                        ),
                        padding="16px 20px",
                    ),
                    height="280px",
                    width="100%",
                    type="hover",
                    scrollbars="vertical",
                ),
                width="100%",
                height="100%",
            ),
            background=TERMINAL_BG,
            border="1px solid rgba(255, 255, 255, 0.1)",
            border_radius="12px",
            width="100%",
            margin_top="24px",
            box_shadow="0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
            overflow="hidden",
            class_name="animate-in",
        ),
    )