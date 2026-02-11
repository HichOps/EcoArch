"""Composant Bloc de pricing et actions - Design Apple-like."""
import reflex as rx

from ..state import State
from .charts import carbon_vs_cost_chart
from src.config import Config

BUDGET_LIMIT = Config.DEFAULT_BUDGET_LIMIT

# Couleurs Apple
APPLE_GREEN = "#34C759"
APPLE_RED = "#FF3B30"
APPLE_ORANGE = "#FF9500"


def pricing_block() -> rx.Component:
    """Bloc d'affichage du prix et actions de déploiement - Style Apple."""
    return rx.box(
        rx.vstack(
            # Label
            rx.text(
                "ESTIMATION MENSUELLE",
                font_size="11px",
                weight="bold",
                letter_spacing="0.08em",
                color="var(--gray-10)",
            ),
            
            # Prix principal avec animation
            rx.hstack(
                rx.text(
                    "$",
                    font_size="32px",
                    weight="medium",
                    color="var(--gray-9)",
                    line_height="1",
                    padding_top="4px",
                ),
                rx.text(
                    f"{State.cost}",
                    font_size="64px",
                    weight="bold",
                    letter_spacing="-0.03em",
                    line_height="1",
                    color=rx.cond(
                        State.cost > BUDGET_LIMIT,
                        APPLE_RED,
                        APPLE_GREEN,
                    ),
                ),
                align="start",
                spacing="1",
            ),
            
            # Badges budget + sobriety (Green Score) avec style Apple
            rx.hstack(
                # Badge budget
                rx.box(
                    rx.hstack(
                        rx.icon(
                            rx.cond(
                                State.cost > BUDGET_LIMIT,
                                "circle-alert",
                                "circle-check",
                            ),
                            size=14,
                            color=rx.cond(
                                State.cost > BUDGET_LIMIT, APPLE_RED, APPLE_GREEN
                            ),
                        ),
                        rx.text(
                            rx.cond(
                                State.cost > BUDGET_LIMIT,
                                "Budget dépassé",
                                "Budget respecté",
                            ),
                            weight="bold",
                            size="2",
                            color=rx.cond(
                                State.cost > BUDGET_LIMIT, APPLE_RED, APPLE_GREEN
                            ),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="8px 16px",
                    border_radius="var(--radius-full)",
                    background=rx.cond(
                        State.cost > BUDGET_LIMIT,
                        f"color-mix(in srgb, {APPLE_RED} 12%, transparent)",
                        f"color-mix(in srgb, {APPLE_GREEN} 12%, transparent)",
                    ),
                ),
                # Badge Sobriety Score (Energy Label)
                rx.tooltip(
                    rx.box(
                        rx.hstack(
                            rx.icon(
                                "leaf",
                                size=14,
                                color=State.score_color,
                            ),
                            rx.text(
                                rx.cond(
                                    State.sobriety_score == "N/A",
                                    "Score ?",
                                    f"Score {State.sobriety_score}",
                                ),
                                weight="bold",
                                size="2",
                                color=State.score_color,
                            ),
                            spacing="2",
                            align="center",
                        ),
                        padding="8px 14px",
                        border_radius="var(--radius-full)",
                        background=f"color-mix(in srgb, {APPLE_GREEN} 6%, var(--gray-1))",
                        border=f"1px solid color-mix(in srgb, {APPLE_GREEN} 24%, transparent)",
                    ),
                    content=State.green_score_tooltip,
                ),
                spacing="3",
                align="center",
            ),
            # Alerte région carbone élevée (optionnel)
            rx.cond(
                State.is_high_carbon_region,
                rx.box(
                    rx.hstack(
                        rx.icon("alert-triangle", size=14, color=APPLE_ORANGE),
                        rx.text(
                            "Région à forte intensité carbone. Envisagez europe-west1 / europe-north1 / europe-west9 si possible.",
                            size="1",
                            color="var(--gray-11)",
                        ),
                        spacing="2",
                        align="start",
                    ),
                    margin_top="8px",
                    padding="8px 12px",
                    border_radius="10px",
                    background=f"color-mix(in srgb, {APPLE_ORANGE} 6%, transparent)",
                    border=f"1px solid color-mix(in srgb, {APPLE_ORANGE} 22%, transparent)",
                ),
            ),
            
            rx.box(height="20px"),
            
            # Bouton Deploy avec style Apple
            _deploy_button(),
            
            rx.box(height="16px"),
            
            # Zone destruction
            _destroy_zone(),
            
            # Graphique donut
            _cost_chart(),
            # Comparatif Coût vs Empreinte
            carbon_vs_cost_chart(),
            
            align="center",
            spacing="3",
            width="100%",
        ),
        padding="32px",
        background=rx.cond(
            State.cost > BUDGET_LIMIT,
            f"color-mix(in srgb, {APPLE_RED} 4%, var(--gray-1))",
            f"color-mix(in srgb, {APPLE_GREEN} 4%, var(--gray-1))",
        ),
        border="1px solid",
        border_color=rx.cond(
            State.cost > BUDGET_LIMIT,
            f"color-mix(in srgb, {APPLE_RED} 20%, transparent)",
            f"color-mix(in srgb, {APPLE_GREEN} 20%, transparent)",
        ),
        border_radius="20px",
        width="100%",
        transition="all 0.3s ease",
        class_name="animate-in",
    )


def _deploy_button() -> rx.Component:
    """Bouton de déploiement avec style Apple."""
    # Désactivé si: non authentifié OU budget dépassé OU coût nul (panier vide)
    is_disabled = (~State.is_authenticated) | (State.cost > BUDGET_LIMIT) | (State.cost == 0)
    
    return rx.button(
        rx.hstack(
            rx.icon("rocket", size=16),
            rx.text("Déployer", weight="bold"),
            spacing="2",
            align="center",
        ),
        on_click=State.start_deployment,
        disabled=is_disabled,
        width="100%",
        size="3",
        radius="large",
        variant="solid",
        cursor=rx.cond(is_disabled, "not-allowed", "pointer"),
        opacity=rx.cond(is_disabled, "0.5", "1"),
        background=rx.cond(
            State.cost > BUDGET_LIMIT,
            "var(--gray-8)",
            rx.cond(
                State.cost == 0,
                "var(--gray-8)",
                APPLE_GREEN,
            ),
        ),
        _hover={
            "opacity": rx.cond(is_disabled, "0.5", "0.9"),
        },
        _active={
            "transform": "scale(0.98)",
        },
        transition="all 0.15s ease",
    )


def _destroy_zone() -> rx.Component:
    """Zone de destruction d'infrastructure avec style Apple."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("trash-2", size=14, color=APPLE_ORANGE),
                rx.text(
                    "Récupération / Nettoyage",
                    size="2",
                    weight="bold",
                    color="var(--gray-11)",
                ),
                spacing="2",
                align="center",
            ),
            rx.input(
                placeholder="ID Infra (ex: f1305d66)",
                on_change=State.set_destroy_id_input,
                size="2",
                variant="surface",
                radius="large",
                width="100%",
            ),
            rx.button(
                rx.hstack(
                    rx.icon("trash", size=14),
                    rx.text("Détruire l'infra", weight="medium"),
                    spacing="2",
                    align="center",
                ),
                on_click=State.start_destruction,
                width="100%",
                size="2",
                variant="outline",
                color_scheme="orange",
                radius="large",
                cursor="pointer",
                _active={
                    "transform": "scale(0.98)",
                },
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        padding="16px",
        border=f"1px solid color-mix(in srgb, {APPLE_ORANGE} 30%, transparent)",
        border_radius="14px",
        background=f"color-mix(in srgb, {APPLE_ORANGE} 6%, transparent)",
    )


def _cost_chart() -> rx.Component:
    """Graphique de répartition des coûts avec couleurs Apple."""
    return rx.cond(
        State.chart_data.length() > 0,
        rx.box(
            rx.recharts.pie_chart(
                rx.recharts.pie(
                    data=State.chart_data,
                    data_key="value",
                    name_key="name",
                    cx="50%",
                    cy="50%",
                    inner_radius=35,
                    outer_radius=55,
                    padding_angle=3,
                    stroke="none",
                    label=True,
                ),
                rx.recharts.legend(
                    icon_type="circle",
                    icon_size=8,
                    vertical_align="bottom",
                    align="center",
                ),
                rx.recharts.graphing_tooltip(),
                width="100%",
                height=200,
            ),
            width="100%",
            margin_top="16px",
            padding_bottom="8px",
        ),
        rx.fragment(),
    )