import reflex as rx
from .state import State
from .components.cards import card_container, stat_card

# --- CSS MINIMALISTE POUR L'ANIMATION PRIX ---
# Une animation de "battement de coeur" pour le prix quand c'est critique
pulse_animation = """
@keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(229, 62, 62, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(229, 62, 62, 0); }
    100% { box-shadow: 0 0 0 0 rgba(229, 62, 62, 0); }
}
@keyframes pulse-green {
    0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(72, 187, 120, 0); }
    100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
}
"""

def resource_item(item: dict, index: int):
    """Ligne du panier (Compatible Clair/Sombre)"""
    icon = rx.cond(
        item["type"] == "compute", "server",
        rx.cond(item["type"] == "sql", "database", "container")
    )

    return rx.box(
        rx.hstack(
            rx.icon(icon, size=18, color=rx.color("indigo", 9)),
            rx.vstack(
                rx.text(item["display_name"], weight="bold", size="2", color=rx.color("slate", 12)),
                rx.cond(
                    item["type"] == "compute",
                    rx.text(f"{item['disk_size']} GB SSD", size="1", color=rx.color("slate", 10)),
                    rx.cond(
                        item["type"] == "sql",
                        rx.text(f"Ver: {item['db_version']}", size="1", color=rx.color("slate", 10)),
                        rx.text("Object Storage", size="1", color=rx.color("slate", 10))
                    )
                ),
                align="start", spacing="1"
            ),
            rx.spacer(),
            rx.button(
                rx.icon("trash-2", size=16),
                on_click=lambda: State.remove_resource(index),
                variant="soft", color_scheme="ruby", size="1",
                cursor="pointer"
            ),
            align="center", width="100%", padding="12px",
            border_bottom=f"1px solid {rx.color('slate', 4)}"
        ),
        width="100%",
        # Style adaptatif : Blanc en mode clair, Gris foncé en mode sombre
        background=rx.color("slate", 2),
        border_radius="8px",
        margin_bottom="8px",
        border=f"1px solid {rx.color('slate', 4)}"
    )

def index():
    return rx.box(
        rx.html(f"<style>{pulse_animation}</style>"),
        
        # --- HEADER (Moderne & Clean) ---
        rx.box(
            rx.container(
                rx.hstack(
                    rx.hstack(
                        rx.icon("leaf", color=rx.color("indigo", 9), size=24),
                        rx.heading("EcoArch", size="6", weight="bold", letter_spacing="-0.5px"),
                        rx.text("V9 Modern", size="6", color=rx.color("slate", 10)),
                        spacing="2", align="center"
                    ),
                    rx.spacer(),
                    # Le bouton pour changer de thème fonctionne parfaitement ici
                    rx.color_mode.button(size="2", variant="soft"),
                    align="center",
                ),
                padding_y="4",
            ),
            position="sticky", top="0", z_index="50",
            backdrop_filter="blur(16px)",
            border_bottom=f"1px solid {rx.color('slate', 4)}",
            width="100%",
            background=rx.color("slate", 1, alpha=True),
        ),

        # --- CONTENU ---
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Architect Builder", value="sim"),
                    rx.tabs.trigger("Gouvernance & Logs", value="gov"),
                    size="2", # <--- CORRECTION DU BUG (3 -> 2)
                ),
                
                # ONGLET 1 : BUILDER
                rx.tabs.content(
                    rx.grid(
                        # GAUCHE : FORMULAIRE
                        rx.vstack(
                            rx.heading("Configuration", size="4", weight="bold"),
                            rx.box(
                                rx.vstack(
                                    rx.text("Type de Service", size="2", weight="bold", color=rx.color("slate", 10)),
                                    rx.select(
                                        ["compute", "sql", "storage"],
                                        value=State.selected_service,
                                        on_change=State.set_service,
                                        width="100%", variant="soft"
                                    ),
                                    rx.divider(margin_y="1rem"),

                                    # COMPUTE
                                    rx.cond(
                                        State.selected_service == "compute",
                                        rx.vstack(
                                            rx.text("Machine", size="2", weight="bold", color=rx.color("slate", 10)),
                                            rx.select(State.instance_types, value=State.selected_machine, on_change=State.set_machine, width="100%"),
                                            rx.hstack(
                                                rx.text("Disque (GB)", size="2", weight="bold", color=rx.color("slate", 10)),
                                                rx.spacer(),
                                                rx.badge(f"{State.selected_storage} GB", variant="soft"),
                                                width="100%", margin_top="1rem"
                                            ),
                                            rx.slider(default_value=[50], min=10, max=1000, on_change=State.set_storage, width="100%"),
                                            width="100%"
                                        )
                                    ),

                                    # SQL
                                    rx.cond(
                                        State.selected_service == "sql",
                                        rx.vstack(
                                            rx.text("Tier", size="2", weight="bold", color=rx.color("slate", 10)),
                                            rx.select(State.db_tiers, value=State.selected_db_tier, on_change=State.set_db_tier, width="100%"),
                                            rx.text("Version", size="2", weight="bold", color=rx.color("slate", 10), margin_top="1rem"),
                                            rx.select(State.db_versions, value=State.selected_db_version, on_change=State.set_db_version, width="100%"),
                                            width="100%"
                                        )
                                    ),

                                    # STORAGE
                                    rx.cond(
                                        State.selected_service == "storage",
                                        rx.vstack(
                                            rx.text("Classe", size="2", weight="bold", color=rx.color("slate", 10)),
                                            rx.select(State.storage_classes, value=State.selected_storage_class, on_change=State.set_storage_class, width="100%"),
                                            width="100%"
                                        )
                                    ),
                                    
                                    rx.button(
                                        rx.hstack(rx.text("Ajouter Ressource"), rx.icon("plus", size=16)),
                                        on_click=State.add_resource,
                                        size="3", width="100%", margin_top="2rem", variant="solid", color_scheme="indigo",
                                        cursor="pointer"
                                    ),
                                    align="start", width="100%", padding="24px"
                                ),
                                # Style Carte : Blanc en clair, Gris foncé en sombre
                                background=rx.color("slate", 2),
                                border=f"1px solid {rx.color('slate', 4)}",
                                border_radius="12px",
                                box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                                width="100%"
                            ),
                            width="100%"
                        ),

                        # DROITE : PRIX & PANIER
                        rx.vstack(
                            rx.heading("Estimation", size="4", weight="bold"),
                            
                            # PANIER
                            rx.box(
                                rx.vstack(
                                    rx.cond(
                                        State.resource_list,
                                        rx.foreach(State.resource_list, resource_item),
                                        rx.center(rx.text("Votre panier est vide", color="gray", font_style="italic"), padding="20px", width="100%")
                                    ),
                                    width="100%", padding="10px"
                                ),
                                background=rx.color("slate", 2),
                                border=f"1px solid {rx.color('slate', 4)}",
                                border_radius="12px",
                                box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                                width="100%"
                            ),
                            
                            # ERREURS
                            rx.cond(
                                State.error_msg != "",
                                rx.callout.root(
                                    rx.callout.icon(rx.icon("triangle-alert")),
                                    rx.callout.text(State.error_msg),
                                    color_scheme="ruby", role="alert", width="100%"
                                )
                            ),

                            # --- BLOC PRIX (FULL COLOR REQUEST) ---
                            # Ce bloc change de couleur selon le budget, en mode clair ET sombre
                            rx.cond(
                                State.cost > 0,
                                rx.box(
                                    rx.vstack(
                                        rx.text(
                                            "ESTIMATION MENSUELLE", 
                                            size="2", weight="bold", letter_spacing="1px",
                                            # Texte coloré selon le statut
                                            color=rx.cond(State.cost <= 50, "var(--green-9)", "var(--red-9)")
                                        ),
                                        
                                        rx.heading(
                                            f"${State.cost:.2f}", # 2 Décimales
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
                                            # Le badge est rempli pour être très visible
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
                                                    # Utilise les couleurs définies dans State.NEON_COLORS
                                                    stroke="none",
                                                    is_animation_active=False # Pas de crash
                                                ),
                                                rx.recharts.legend(), height=180, width="100%"
                                            ),
                                            width="100%"
                                        ),
                                        spacing="4", align="center", width="100%"
                                    ),
                                    
                                    # STYLE DYNAMIQUE
                                    # Fond teinté léger (Vert ou Rouge)
                                    background=rx.cond(
                                        State.cost <= 50,
                                        rx.color("green", 3),
                                        rx.color("red", 3)
                                    ),
                                    # Bordure solide (Vert ou Rouge)
                                    border=rx.cond(
                                        State.cost <= 50,
                                        f"2px solid {rx.color('green', 9)}",
                                        f"2px solid {rx.color('red', 9)}"
                                    ),
                                    # Animation pulsation
                                    style={
                                        "animation": rx.cond(State.cost <= 50, "pulse-green 3s infinite", "pulse-red 1s infinite")
                                    },
                                    border_radius="12px",
                                    padding="24px",
                                    width="100%"
                                )
                            ),
                            
                            rx.cond(State.is_loading, rx.center(rx.spinner(size="3"), width="100%", padding="2rem")),
                            width="100%", spacing="6"
                        ),
                        columns="2", spacing="8", width="100%"
                    ),
                    value="sim", padding_top="2rem",
                ),

                # ONGLET 2 : GOUVERNANCE
                rx.tabs.content(
                    rx.vstack(
                        rx.heading("Dashboard FinOps", size="6", weight="bold", margin_bottom="1rem"),
                        rx.grid(
                            stat_card("Dernier Coût", State.last_run_cost, "Pipeline", "dollar-sign", "indigo"),
                            stat_card("Statut", State.last_run_status, "Conformité", "shield-check", State.last_run_color),
                            stat_card("Budget", "50.00 $", "Limite", "target", "gray"),
                            columns="3", spacing="4", width="100%"
                        ),
                        rx.box(
                             rx.vstack(
                                rx.text("Historique", weight="bold", size="3"),
                                rx.recharts.area_chart(
                                    rx.recharts.area(
                                        data_key="total_monthly_cost", 
                                        stroke="#8884d8", fill="#8884d8",
                                        is_animation_active=False
                                    ),
                                    rx.recharts.x_axis(data_key="display_date"),
                                    rx.recharts.y_axis(),
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                    data=State.history,
                                    height=300, width="100%",
                                ),
                                width="100%", padding="20px"
                             ),
                             background=rx.color("slate", 2), 
                             border=f"1px solid {rx.color('slate', 4)}",
                             border_radius="12px", width="100%"
                        ),
                        
                        # TABLEAU
                        rx.box(
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
                                            rx.table.cell(f"{item['total_monthly_cost']} $", font_weight="bold"),
                                            rx.table.cell(rx.badge(item["status"], variant="solid", color_scheme=rx.cond(item["status"] == "PASSED", "green", "red"))),
                                        )
                                    )
                                ),
                                variant="surface", width="100%",
                            ),
                            border_radius="12px", overflow="hidden", width="100%",
                            border=f"1px solid {rx.color('slate', 4)}"
                        ),
                        spacing="6", width="100%",
                    ),
                    value="gov", padding_top="2rem",
                ),
                default_value="sim", width="100%",
            ),
            size="2", # Taille d'onglet standard supportée
        ),
        
        # FOND GLOBAL : S'adapte au mode clair (blanc) / sombre (gris)
        background=rx.color("slate", 1),
        min_height="100vh",
        font_family="Inter",
    )

app = rx.App(theme=rx.theme(appearance="light", accent_color="indigo", radius="large"))
app.add_page(index, title="EcoArch V9 Modern", on_load=State.load_history)