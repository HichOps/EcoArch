import reflex as rx
from .state import State
from .styles import GLOBAL_ANIMATIONS

# Import des composants modulaires
from .components.header import header
from .components.form import configuration_form
from .components.resources import resource_list_display
from .components.pricing import pricing_block
from .components.stats import governance_dashboard
# Import du nouveau composant Logs
from .components.logs import deploy_console

def index():
    return rx.box(
        # Injection CSS Global
        rx.html(f"<style>{GLOBAL_ANIMATIONS}</style>"),
        
        # 1. Header
        header(),

        # 2. Contenu Principal
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Architect Builder", value="sim"),
                    rx.tabs.trigger("Gouvernance & Logs", value="gov"),
                    size="2",
                ),
                
                # --- ONGLET BUILDER ---
                rx.tabs.content(
                    rx.vstack(  # Utilisation d'un vstack pour empiler Grille + Console
                        rx.grid(
                            # Colonne Gauche : Formulaire
                            configuration_form(),

                            # Colonne Droite : Panier + Prix
                            rx.vstack(
                                resource_list_display(),
                                
                                # Zone d'erreurs
                                rx.cond(
                                    State.error_msg != "",
                                    rx.callout.root(
                                        rx.callout.icon(rx.icon("triangle-alert")),
                                        rx.callout.text(State.error_msg),
                                        color_scheme="ruby", role="alert", width="100%"
                                    )
                                ),

                                # Bloc Prix Néon
                                pricing_block(),
                                
                                rx.cond(State.is_loading, rx.center(rx.spinner(size="3"), width="100%", padding="2rem")),
                                width="100%", spacing="6"
                            ),
                            columns="2", spacing="8", width="100%"
                        ),
                        
                        # --- CONSOLE DE DÉPLOIEMENT (NOUVEAU) ---
                        deploy_console(),
                        # ----------------------------------------
                        
                        width="100%", spacing="6"
                    ),
                    value="sim", padding_top="2rem",
                ),

                # --- ONGLET GOUVERNANCE ---
                rx.tabs.content(
                    governance_dashboard(),
                    value="gov", padding_top="2rem",
                ),
                default_value="sim", width="100%",
            ),
            size="2",
        ),
        
        background=rx.color("slate", 1),
        min_height="100vh",
        font_family="Inter",
    )

app = rx.App(theme=rx.theme(appearance="light", accent_color="indigo", radius="large"))
app.add_page(index, title="EcoArch V9 Modular", on_load=State.load_history)