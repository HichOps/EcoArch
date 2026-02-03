"""Composant Console de déploiement."""
import reflex as rx

from ..state import State

# Couleur néon pour le terminal
NEON_GREEN = "#39ff14"


def log_line(line: str) -> rx.Component:
    """Affiche une ligne de log."""
    return rx.text(
        line,
        font_family="monospace",
        font_size="12px",
        color=NEON_GREEN,
    )


def deploy_console() -> rx.Component:
    """Console de déploiement affichée pendant les opérations."""
    return rx.cond(
        State.is_deploying,
        rx.box(
            rx.vstack(
                # En-tête
                rx.hstack(
                    rx.icon("terminal", color=NEON_GREEN, size=18),
                    rx.text(
                        "TERMINAL DE DÉPLOIEMENT - LIVE",
                        weight="bold",
                        color=NEON_GREEN,
                        size="2",
                    ),
                    rx.spacer(),
                    rx.cond(
                        State.deploy_status == "running",
                        rx.spinner(color=NEON_GREEN, size="2"),
                        rx.icon("circle-check", color=NEON_GREEN, size=18),
                    ),
                    width="100%",
                    padding_bottom="10px",
                    border_bottom="1px solid #333",
                ),
                # Zone de logs scrollable
                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(State.logs, log_line),
                        align="start",
                        spacing="1",
                    ),
                    height="300px",
                    width="100%",
                    type="always",
                    scrollbars="vertical",
                ),
                width="100%",
                height="100%",
            ),
            background="black",
            border="2px solid #333",
            border_radius="8px",
            padding="15px",
            width="100%",
            margin_top="20px",
            box_shadow=f"0 0 20px rgba(57, 255, 20, 0.2)",
        ),
    )