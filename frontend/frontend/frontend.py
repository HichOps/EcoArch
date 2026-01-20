import reflex as rx
from .state import State
from .components.cards import price_hero, card_container, stat_card

# --- STYLE GLOBAL ---
bg_style = {
    "background": "radial-gradient(circle at 50% 0%, #eef2ff 0%, #f8fafc 100%)",
    "min_height": "100vh",
}

def index():
    return rx.box(
        # --- HEADER ---
        rx.box(
            rx.container(
                rx.hstack(
                    rx.hstack(
                        rx.icon("leaf", color=rx.color("grass", 9), size=24),
                        rx.heading("EcoArch", size="6", weight="bold", letter_spacing="-1px"),
                        rx.text("Platform", size="6", weight="medium", color=rx.color("slate", 10)),
                        spacing="2",
                        align="center"
                    ),
                    rx.spacer(),
                    rx.badge("Control Plane", variant="outline", color_scheme="gray", radius="full"),
                    width="100%",
                    align="center",
                ),
                padding_y="5",
            ),
            position="sticky", top="0", z_index="50",
            backdrop_filter="blur(12px)",
            border_bottom="1px solid rgba(255,255,255,0.5)",
            width="100%",
        ),

        # --- CONTENU PRINCIPAL ---
        rx.container(
            rx.tabs.root(
                # --- NAVIGATION ONGLETS ---
                rx.tabs.list(
                    rx.tabs.trigger("Gouvernance Dashboard", value="gov"),
                    rx.tabs.trigger("Simulateur Temps Réel", value="sim"),
                    size="2",
                ),
                
                # =========================================
                # ONGLET 1 : GOUVERNANCE
                # =========================================
                rx.tabs.content(
                    rx.vstack(
                        rx.heading("Vue d'ensemble CI/CD", size="7", weight="bold", margin_y="1rem"),
                        
                        # KPI GRID
                        rx.grid(
                            stat_card("Dernier Coût", State.last_run_cost, "Pipeline GitLab", "dollar-sign", "indigo"),
                            stat_card("Statut", State.last_run_status, "Conformité Budget", "shield-check", State.last_run_color),
                            stat_card("Budget Limite", "50.00 $", "Référentiel Hard Limit", "target", "gray"),
                            columns="3",
                            spacing="4",
                            width="100%"
                        ),
                        
                        # GRAPHIQUE HISTORIQUE
                        card_container(
                             rx.vstack(
                                rx.text("Évolution des coûts", weight="bold", size="3", color=rx.color("slate", 11)),
                                rx.recharts.area_chart(
                                    rx.recharts.area(
                                        data_key="total_monthly_cost",
                                        stroke="#10b981",
                                        fill="#10b981",
                                        fill_opacity=0.2
                                    ),
                                    rx.recharts.x_axis(data_key="display_date"),
                                    rx.recharts.y_axis(),
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                    rx.recharts.tooltip(),
                                    data=State.history,
                                    height=300,
                                    width="100%",
                                ),
                                align="start",
                                width="100%"
                             )
                        ),
                        
                        # TABLEAU
                        rx.box(
                            rx.heading("Derniers déploiements", size="4", margin_bottom="1rem"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("Date"),
                                        rx.table.column_header_cell("Auteur"),
                                        rx.table.column_header_cell("Branche"),
                                        rx.table.column_header_cell("Coût"),
                                        rx.table.column_header_cell("Statut"),
                                    ),
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        State.history,
                                        lambda item: rx.table.row(
                                            rx.table.cell(item["display_date"]),
                                            rx.table.cell(item["author"]),
                                            rx.table.cell(item["branch_name"]),
                                            rx.table.cell(f"{item['total_monthly_cost']} $"),
                                            rx.table.cell(
                                                rx.badge(
                                                    item["status"], 
                                                    color_scheme=rx.cond(item["status"] == "PASSED", "grass", "tomato")
                                                )
                                            ),
                                        )
                                    )
                                ),
                                variant="surface",
                                width="100%",
                            ),
                            margin_top="2rem",
                            width="100%"
                        ),
                        
                        spacing="6",
                        width="100%",
                    ),
                    value="gov",
                    padding_top="2rem",
                ),

                # =========================================
                # ONGLET 2 : SIMULATEUR
                # =========================================
                rx.tabs.content(
                    rx.grid(
                        # Configuration (Gauche)
                        card_container(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("sliders-horizontal", size=18),
                                    rx.text("Paramètres", weight="bold", size="3"),
                                    margin_bottom="1rem",
                                    color=rx.color("slate", 11)
                                ),
                                rx.text("Région", size="2", weight="bold"),
                                rx.select(State.regions, value=State.region, on_change=State.set_region, width="100%", variant="soft"),
                                rx.text("Instance", size="2", weight="bold", margin_top="1rem"),
                                rx.select(State.instance_types, value=State.instance_type, on_change=State.set_instance_type, width="100%", variant="soft"),
                                rx.hstack(rx.text("Stockage"), rx.spacer(), rx.badge(f"{State.storage} GB")),
                                rx.slider(default_value=[50], min=10, max=1000, on_change=State.set_storage_value, width="100%"),
                                rx.button(
                                    rx.hstack(rx.text("Lancer l'estimation"), rx.icon("sparkles", size=16)),
                                    on_click=State.run_simulation,
                                    loading=State.is_loading,
                                    size="4", width="100%", margin_top="2rem", variant="solid", color_scheme="grass",
                                    style={"box_shadow": "0 10px 15px -3px rgba(34, 197, 94, 0.4)"}
                                ),
                                width="100%"
                            ),
                            bg_color="white"
                        ),
                        # Résultats (Droite)
                        rx.box(
                            rx.cond(
                                State.cost > 0,
                                rx.vstack(
                                    price_hero(State.cost, State.budget_accent_color, State.budget_icon, State.budget_label),
                                    card_container(
                                        rx.recharts.pie_chart(
                                            rx.recharts.pie(data=State.chart_data, data_key="value", name_key="name", cx="50%", cy="50%", inner_radius=70, outer_radius=90, fill="#8884d8", padding_angle=2),
                                            rx.recharts.legend(), height=250, width="100%"
                                        ),
                                        bg_color="rgba(255,255,255,0.6)"
                                    ),
                                    width="100%", spacing="5"
                                ),
                                rx.center(
                                    rx.vstack(
                                        rx.icon("bar-chart-2", size=64, color=rx.color("slate", 5)),
                                        rx.text("En attente de configuration", weight="bold", color=rx.color("slate", 8)),
                                        spacing="4", align="center"
                                    ),
                                    height="100%", min_height="400px", border=f"2px dashed {rx.color('slate', 6)}", border_radius="24px", bg="rgba(255,255,255,0.3)"
                                )
                            )
                        ),
                        columns="2", spacing="8", width="100%"
                    ),
                    value="sim",
                    padding_top="2rem",
                ),
                
                default_value="gov",
                width="100%",
            ),
            size="3",
        ),
        style=bg_style,
        font_family="Inter",
    )

app = rx.App(theme=rx.theme(appearance="light", accent_color="grass", radius="large"))
app.add_page(index, title="EcoArch Control Plane", on_load=State.load_history)