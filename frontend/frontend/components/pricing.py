import reflex as rx
from ..state import State

def pricing_block():
    return rx.box(
        rx.vstack(
            rx.text(
                "ESTIMATION MENSUELLE", 
                size="2", weight="bold", letter_spacing="1px",
                color=rx.cond(State.cost <= 50, "var(--green-9)", "var(--red-9)")
            ),
            
            rx.heading(
                f"${State.cost:.2f}", 
                size="9", weight="bold",
                color=rx.cond(State.cost <= 50, "var(--green-9)", "var(--red-9)"), 
            ),
            
            rx.badge(
                rx.hstack(
                    rx.icon(rx.cond(State.cost <= 50, "circle-check", "triangle-alert"), size=16),
                    rx.text(rx.cond(State.cost <= 50, "Budget Respecté", "Budget Explosé"))
                ),
                variant="solid",
                color_scheme=rx.cond(State.cost <= 50, "green", "red"),
                radius="full", padding="0.5rem 1rem"
            ),

            rx.divider(margin_y="10px", opacity="0.2"),

            # --- ZONE D'ACTIONS ---
            rx.vstack(
                # BOUTON 1 : DÉPLOYER
                rx.cond(
                    State.cost <= 50,
                    rx.button(
                        rx.hstack(rx.icon("rocket", size=20), rx.text("DÉPLOYER", weight="bold")),
                        on_click=State.start_deployment,
                        loading=State.is_deploying,
                        disabled=State.is_deploying,
                        width="100%", size="4", color_scheme="ruby", variant="solid",
                        box_shadow="0 0 20px rgba(229, 62, 62, 0.4)",
                        _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
                    ),
                    rx.button(
                        rx.hstack(rx.icon("lock", size=20), rx.text("BUDGET DÉPASSÉ", weight="bold")),
                        disabled=True, width="100%", size="4", color_scheme="gray", variant="soft"
                    )
                ),

                # BOUTON 2 : DÉTRUIRE
                rx.button(
                    rx.hstack(rx.icon("trash-2", size=18), rx.text("DÉTRUIRE L'INFRA", weight="bold")),
                    on_click=State.start_destruction,
                    disabled=State.is_deploying, 
                    width="100%", 
                    size="3", 
                    variant="outline", 
                    color_scheme="orange",
                    title="Supprime l'infra liée à cet ID"
                ),
                spacing="3", width="100%"
            ),

            # Graphique
            rx.cond(
                State.cost > 0,
                rx.box(
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=State.chart_data, 
                            data_key="value", name_key="name",
                            cx="50%", cy="50%", inner_radius=50, outer_radius=70, 
                            stroke="none", is_animation_active=False
                        ),
                        rx.recharts.legend(), height=180, width="100%"
                    ),
                    width="100%"
                )
            ),
            spacing="4", align="center", width="100%"
        ),
        background=rx.cond(State.cost <= 50, rx.color("green", 3), rx.color("red", 3)),
        border=rx.cond(State.cost <= 50, f"2px solid {rx.color('green', 9)}", f"2px solid {rx.color('red', 9)}"),
        border_radius="12px", padding="24px", width="100%", box_shadow="0 4px 20px rgba(0,0,0,0.1)"
    )