import reflex as rx
from ..state import State

def pricing_block():
    return rx.box(
        rx.vstack(
            # --- 1. SÉLECTEUR D'UTILISATEUR ---
            rx.box(
                rx.text("QUI ÊTES-VOUS ?", font_size="10px", font_weight="bold", opacity=0.7, letter_spacing="1px"),
                rx.select(
                    State.users_list,
                    value=State.current_user,
                    on_change=State.set_user,
                    size="2",
                    variant="soft",
                    color_scheme="violet",
                    radius="full",
                    width="100%",
                ),
                width="100%", margin_bottom="10px"
            ),

            # --- 2. AFFICHAGE ID INFRASTRUCTURE ---
            rx.vstack(
                rx.hstack(
                    rx.text("ID SESSION / INFRA :", font_size="10px", font_weight="bold", opacity=0.7),
                    rx.spacer(),
                    rx.icon("refresh-cw", size=14, on_click=State.generate_new_id, cursor="pointer", title="Générer un nouvel ID"),
                    width="100%", align="center"
                ),
                rx.input(
                    value=State.deployment_id,
                    on_change=State.set_deployment_id,
                    placeholder="Entrez l'ID de l'infra (ex: a1b2c3d4)",
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                    radius="full",
                    font_family="monospace",
                    text_align="center",
                    width="100%",
                    border="1px solid rgba(255,255,255,0.1)"
                ),
                margin_bottom="15px", width="100%"
            ),

            # --- 3. ESTIMATION ---
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

            # --- 4. ZONE D'ACTIONS ---
            rx.vstack(
                # BOUTON DÉPLOYER
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

                # BOUTON DÉTRUIRE
                rx.button(
                    rx.hstack(rx.icon("trash-2", size=18), rx.text("DÉTRUIRE L'INFRA", weight="bold")),
                    on_click=State.start_destruction,
                    disabled=State.is_deploying, 
                    width="100%", 
                    size="3", 
                    variant="outline", 
                    color_scheme="orange",
                    title="Supprime l'infra liée à cet ID uniquement"
                ),
                spacing="3", width="100%"
            ),

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