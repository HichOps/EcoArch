"""Composants de visualisation GreenOps (Coût vs Empreinte)."""

import reflex as rx

from ..state import State


def carbon_vs_cost_chart() -> rx.Component:
    """Graphique comparatif simple Coût ($) vs Empreinte (Sobriety Score)."""
    # Mapping A–E → 1–5 pour l'affichage
    footprint_value = rx.cond(
        State.sobriety_score == "A",
        1,
        rx.cond(
            State.sobriety_score == "B",
            2,
            rx.cond(
                State.sobriety_score == "C",
                3,
                rx.cond(
                    State.sobriety_score == "D",
                    4,
                    5,
                ),
            ),
        ),
    )

    data = [
        {"name": "Coût ($)", "value": State.cost},
        {"name": "Empreinte (A→E)", "value": footprint_value},
    ]

    return rx.box(
        rx.text(
            "Coût vs Empreinte",
            size="2",
            weight="medium",
            color="var(--gray-11)",
            margin_bottom="6px",
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.x_axis(data_key="name"),
            rx.recharts.y_axis(),
            rx.recharts.bar(data_key="value", fill="var(--accent-9)", radius=6),
            data=data,
            width="100%",
            height=180,
        ),
        width="100%",
        margin_top="8px",
    )

