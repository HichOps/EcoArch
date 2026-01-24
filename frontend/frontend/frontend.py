import reflex as rx
from .state import State
from .components.cards import price_hero, card_container, stat_card

bg_style = {
    "background": "radial-gradient(circle at 50% 0%, #eef2ff 0%, #f8fafc 100%)",
    "min_height": "100vh",
}

def resource_item(item: dict, index: int):
    """Affiche un élément du panier avec une icône adaptée"""
    # Choix de l'icône selon le type
    icon = rx.cond(item["type"] == "sql", "database", "server")
    
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=18, color=rx.color("indigo", 9)),
            rx.vstack(
                rx.text(item["display_name"], weight="bold", size="2"),
                rx.cond(
                    item["type"] == "compute",
                    rx.text(f"{item['disk_size']} GB SSD", size="1", color=rx.color("slate", 10)),
                    rx.text(f"Ver: {item['db_version']}", size="1", color=rx.color("slate", 10))
                ),
                align="start", spacing="1"
            ),
            rx.spacer(),
            rx.button(
                rx.icon("trash-2", size=16),
                on_click=lambda: State.remove_resource(index),
                variant="ghost", color_scheme="ruby", size="1"
            ),
            align="center", width="100%", padding="12px",
            border_bottom=f"1px solid {rx.color('slate', 4)}"
        ),
        width="100%"
    )

def index():
    return rx.box(
        # HEADER
        rx.box(
            rx.container(
                rx.hstack(
                    rx.hstack(
                        rx.icon("leaf", color=rx.color("grass", 9), size=24),
                        rx.heading("EcoArch", size="6", weight="bold"),
                        rx.text("Architect", size="6", color=rx.color("slate", 10)),
                        spacing="2", align="center"
                    ),
                    rx.spacer(),
                    rx.badge("V3 Multi-Service", variant="outline", color_scheme="indigo", radius="full"),
                    width="100%", align="center",
                ),
                padding_y="5",
            ),
            position="sticky", top="0", z_index="50",
            backdrop_filter="blur(12px)", border_bottom="1px solid rgba(255,255,255,0.5)", width="100%",
        ),

        # CONTENU
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Architecture Builder", value="sim"),
                    rx.tabs.trigger("Gouvernance", value="gov"),
                    size="2",
                ),
                
                # --- ONGLET 1 : BUILDER ---
                rx.tabs.content(
                    rx.grid(
                        # COLONNE GAUCHE : FORMULAIRE
                        rx.vstack(
                            rx.heading("Configurer un service", size="4", weight="bold"),
                            card_container(
                                rx.vstack(
                                    rx.text("Type de Service", size="2", weight="bold", color=rx.color("slate", 10)),
                                    # SELECTEUR PRINCIPAL (Compute vs SQL)
                                    rx.select(
                                        ["compute", "sql"],
                                        value=State.selected_service,
                                        on_change=State.set_service,
                                        width="100%", variant="soft"
                                    ),
                                    
                                    rx.divider(margin_y="1rem"),

                                    # --- FORMULAIRE COMPUTE (VM) ---
                                    rx.cond(
                                        State.selected_service == "compute",
                                        rx.vstack(
                                            rx.text("Configuration Machine", size="2", weight="bold", color=rx.color("slate", 10)),
                                            rx.select(
                                                State.instance_types,
                                                value=State.selected_machine,
                                                on_change=State.set_machine,
                                                width="100%", variant="soft",
                                            ),
                                            rx.text("Stockage SSD", size="2", weight="bold", color=rx.color("slate", 10), margin_top="1rem"),
                                            rx.badge(f"{State.selected_storage} GB", variant="solid", color_scheme="indigo", radius="full"),
                                            rx.slider(
                                                default_value=[50], min=10, max=1000,
                                                on_change=State.set_storage,
                                                width="100%", color_scheme="indigo",
                                            ),
                                            width="100%"
                                        )
                                    ),

                                    # --- FORMULAIRE SQL (DATABASE) ---
                                    rx.cond(
                                        State.selected_service == "sql",
                                        rx.vstack(
                                            rx.text("Puissance (Tier)", size="2", weight="bold", color=rx.color("slate", 10)),
                                            rx.select(
                                                State.db_tiers,
                                                value=State.selected_db_tier,
                                                on_change=State.set_db_tier,
                                                width="100%", variant="soft",
                                            ),
                                            rx.text("Version Moteur", size="2", weight="bold", color=rx.color("slate", 10), margin_top="1rem"),
                                            rx.select(
                                                State.db_versions,
                                                value=State.selected_db_version,
                                                on_change=State.set_db_version,
                                                width="100%", variant="soft",
                                            ),
                                            width="100%"
                                        )
                                    ),
                                    
                                    # BOUTON AJOUTER
                                    rx.button(
                                        rx.hstack(rx.text("Ajouter au panier"), rx.icon("plus", size=16)),
                                        on_click=State.add_resource,
                                        size="3", width="100%", margin_top="2rem",
                                        variant="solid", color_scheme="indigo",
                                    ),
                                    align="start", width="100%"
                                ),
                                bg_color="white"
                            ),
                            width="100%"
                        ),

                        # COLONNE DROITE : PANIER
                        rx.vstack(
                            rx.heading("Votre Infrastructure", size="4", weight="bold"),
                            card_container(
                                rx.vstack(
                                    rx.cond(
                                        State.resource_list,
                                        rx.foreach(State.resource_list, resource_item),
                                        rx.center(rx.text("Panier vide", color="gray", style={"font_style": "italic"}), padding="20px", width="100%")
                                    ),
                                    width="100%"
                                ),
                                bg_color="rgba(255,255,255,0.9)"
                            ),
                            
                            # ERREURS (Correction Icône ici)
                            rx.cond(
                                State.error_msg != "",
                                rx.callout.root(
                                    rx.callout.icon(rx.icon("triangle-alert")), # <--- NOM CORRIGÉ
                                    rx.callout.text(State.error_msg),
                                    color_scheme="ruby", role="alert", width="100%"
                                )
                            ),

                            # PRIX TOTAL (Correction Logic ici)
                            rx.cond(
                                State.cost > 0,
                                rx.vstack(
                                    # <--- CORRECTION MAJEURE ICI : Utilisation de rx.cond au lieu de if/else
                                    price_hero(
                                        State.cost, 
                                        rx.cond(State.cost <= 50, "grass", "tomato"), 
                                        "check", 
                                        "Total Mensuel"
                                    ),
                                    
                                    card_container(
                                        rx.recharts.pie_chart(
                                            rx.recharts.pie(
                                                data=State.chart_data, data_key="value", name_key="name",
                                                cx="50%", cy="50%", inner_radius=60, outer_radius=80, fill="#8884d8"
                                            ),
                                            rx.recharts.legend(), height=200, width="100%"
                                        ),
                                        bg_color="rgba(255,255,255,0.5)"
                                    ),
                                    width="100%", spacing="4"
                                )
                            ),
                            
                            # SPINNER
                            rx.cond(
                                State.is_loading,
                                rx.center(rx.spinner(color="indigo", size="3"), width="100%", padding="2rem")
                            ),
                            width="100%", spacing="4"
                        ),
                        columns="2", spacing="8", width="100%"
                    ),
                    value="sim", padding_top="2rem",
                ),

                # --- ONGLET 2 : GOUVERNANCE ---
                rx.tabs.content(
                    rx.center(rx.text("Historique des coûts (voir State.py pour implémentation complète)")),
                    value="gov", padding_top="2rem",
                ),
                
                default_value="sim", width="100%",
            ),
            size="3",
        ),
        style=bg_style, font_family="Inter",
    )

app = rx.App(theme=rx.theme(appearance="light", accent_color="indigo", radius="large"))
app.add_page(index, title="EcoArch V3", on_load=State.load_history)