import reflex as rx
from ..state import State

def log_line(line: str):
    return rx.text(
        line, 
        font_family="monospace", 
        font_size="12px", 
        color="#39ff14" # Vert Néon
    )

def deploy_console():
    return rx.cond(
        State.is_deploying, # S'affiche seulement si déploiement actif ou terminé
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("terminal", color="#39ff14", size=18),
                    rx.text("TERMINAL DE DÉPLOIEMENT - LIVE", weight="bold", color="#39ff14", size="2"),
                    rx.spacer(),
                    rx.cond(
                        State.deploy_status == "running",
                        rx.spinner(color="#39ff14", size="2"),
                        # CORRECTION ICI : "circle-check" au lieu de "check-circle"
                        rx.icon("circle-check", color="#39ff14", size=18)
                    ),
                    width="100%", padding_bottom="10px", border_bottom="1px solid #333"
                ),
                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(State.logs, log_line),
                        align="start", spacing="1"
                    ),
                    height="300px",
                    width="100%",
                    type="always",
                    scrollbars="vertical",
                ),
                width="100%", height="100%"
            ),
            background="black",
            border="2px solid #333",
            border_radius="8px",
            padding="15px",
            width="100%",
            margin_top="20px",
            box_shadow="0 0 20px rgba(57, 255, 20, 0.2)"
        )
    )