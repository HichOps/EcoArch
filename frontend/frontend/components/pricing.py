"""Composant Bloc de pricing et actions."""
import reflex as rx

from ..state import State
from src.config import Config

BUDGET_LIMIT = Config.DEFAULT_BUDGET_LIMIT


def pricing_block() -> rx.Component:
    """Bloc d'affichage du prix et actions de déploiement."""
    return rx.box(
        rx.vstack(
            # Label
            rx.text(
                "ESTIMATION MENSUELLE",
                font_size="10px",
                weight="bold",
                letter_spacing="1px",
                color="var(--gray-11)",
            ),
            
            # Prix principal
            rx.text(
                f"${State.cost}",
                font_size="48px",
                weight="bold",
                color=rx.cond(
                    State.cost > BUDGET_LIMIT,
                    "var(--ruby-9)",
                    "var(--grass-9)",
                ),
            ),
            
            # Badge budget
            rx.badge(
                rx.cond(
                    State.cost > BUDGET_LIMIT,
                    "Budget Explosé",
                    "Budget Respecté",
                ),
                color_scheme=rx.cond(State.cost > BUDGET_LIMIT, "ruby", "grass"),
                variant="solid",
                radius="full",
                padding_x="10px",
            ),
            
            rx.divider(margin_y="20px", width="100%"),
            
            # Bouton Deploy
            _deploy_button(),
            
            rx.divider(margin_y="10px", width="100%", opacity="0"),
            
            # Zone destruction
            _destroy_zone(),
            
            # Graphique donut
            _cost_chart(),
            
            align="center",
            spacing="4",
        ),
        padding="30px",
        background=rx.cond(
            State.cost > BUDGET_LIMIT,
            "var(--ruby-2)",
            "var(--green-2)",
        ),
        border="1px solid",
        border_color=rx.cond(
            State.cost > BUDGET_LIMIT,
            "var(--ruby-6)",
            "var(--green-6)",
        ),
        border_radius="16px",
        width="100%",
    )


def _deploy_button() -> rx.Component:
    """Bouton de déploiement."""
    return rx.button(
        rx.hstack(
            rx.icon("rocket", size=18),
            rx.text("DÉPLOYER"),
        ),
        on_click=State.start_deployment,
        disabled=State.cost > BUDGET_LIMIT,
        width="100%",
        size="3",
        color_scheme=rx.cond(State.cost > BUDGET_LIMIT, "ruby", "grass"),
        variant="solid",
        cursor=rx.cond(State.cost > BUDGET_LIMIT, "not-allowed", "pointer"),
        opacity=rx.cond(State.cost > BUDGET_LIMIT, "0.5", "1"),
    )


def _destroy_zone() -> rx.Component:
    """Zone de destruction d'infrastructure."""
    return rx.box(
        rx.vstack(
            rx.text(
                "Récupération / Nettoyage",
                size="1",
                weight="bold",
                color="gray",
            ),
            rx.input(
                placeholder="ID Infra (ex: f1305d66)",
                on_change=State.set_destroy_id_input,
                size="2",
                variant="soft",
                radius="medium",
                width="100%",
            ),
            rx.button(
                rx.hstack(
                    rx.icon("trash", size=16),
                    rx.text("DÉTRUIRE L'INFRA"),
                ),
                on_click=State.start_destruction,
                width="100%",
                size="2",
                variant="outline",
                color_scheme="orange",
            ),
            spacing="2",
            width="100%",
        ),
        width="100%",
        padding="10px",
        border="1px dashed var(--orange-6)",
        border_radius="8px",
        background="var(--orange-2)",
    )


def _cost_chart() -> rx.Component:
    """Graphique de répartition des coûts."""
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            data=State.chart_data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            inner_radius=40,
            outer_radius=60,
            padding_angle=2,
        ),
        rx.recharts.legend(),
        height=200,
        width="100%",
    )