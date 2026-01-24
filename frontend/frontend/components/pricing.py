import reflex as rx
from ..state import State
from ..styles import NEON_GREEN, NEON_RED

def pricing_block():
    return rx.cond(
        State.cost > 0,
        rx.box(
            rx.vstack(
                rx.text(
                    "ESTIMATION MENSUELLE", 
                    size="2", weight="bold", letter_spacing="1px",
                    color=rx.cond(State.cost <= 50, "var(--green-9)", "var(--red-9)")
                ),
                
                rx.heading(
                    f"${State.cost:.2f}", 
                    size="9", 
                    weight="bold",
                    color=rx.cond(State.cost <= 50, "var(--green-9)", "var(--red-9)"), 
                ),
                
                rx.badge(
                    rx.hstack(
                        rx.icon(rx.cond(State.cost <= 50, "check", "triangle-alert"), size=16),
                        rx.text(rx.cond(State.cost <= 50, "Budget Respecté", "Budget Explosé"))
                    ),
                    variant="solid",
                    color_scheme=rx.cond(State.cost <= 50, "green", "red"),
                    radius="full",
                    padding="0.5rem 1rem"
                ),

                rx.box(
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=State.chart_data, 
                            data_key="value", name_key="name",
                            cx="50%", cy="50%", inner_radius=50, outer_radius=70, 
                            stroke="none",
                            is_animation_active=False
                        ),
                        rx.recharts.legend(), height=180, width="100%"
                    ),
                    width="100%"
                ),
                spacing="4", align="center", width="100%"
            ),
            
            # STYLES DYNAMIQUES
            background=rx.cond(
                State.cost <= 50,
                rx.color("green", 3),
                rx.color("red", 3)
            ),
            border=rx.cond(
                State.cost <= 50,
                f"2px solid {rx.color('green', 9)}",
                f"2px solid {rx.color('red', 9)}"
            ),
            style={
                "animation": rx.cond(State.cost <= 50, "pulse-green 3s infinite", "pulse-red 1s infinite")
            },
            border_radius="12px",
            padding="24px",
            width="100%"
        )
    )