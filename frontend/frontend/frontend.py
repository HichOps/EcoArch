import reflex as rx
from .state import State
from .styles import GLOBAL_ANIMATIONS

# --- IMPORTS DES COMPOSANTS ---
from .components.header import header
from .components.topbar import user_topbar
from .components.form import configuration_form
from .components.resources import resource_list_display
from .components.pricing import pricing_block
from .components.stats import governance_dashboard
from .components.logs import deploy_console
from .components.wizard import wizard_block 
from .components.audit_view import audit_log_table # <-- Le tableau de logs

def index():
    return rx.box(
        # Injection des animations CSS globales
        rx.html(f"<style>{GLOBAL_ANIMATIONS}</style>"),
        
        # 1. BARRE D'IDENTITÉ (Sticky Top)
        user_topbar(),

        # 2. HEADER DU PROJET
        header(),

        # 3. CONTENU PRINCIPAL
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Architect Builder", value="sim"),
                    rx.tabs.trigger("Gouvernance & Logs", value="gov"),
                    size="2",
                ),
                
                # ==================================================
                # ONGLET 1 : BUILDER (Expert & Assistant)
                # ==================================================
                rx.tabs.content(
                    rx.vstack(  
                        # A. SWITCH MODE (Assistant / Expert)
                        rx.center(
                            rx.hstack(
                                rx.text("Mode Assistant", weight="bold", 
                                        color=rx.cond(~State.is_expert_mode, "var(--violet-9)", "var(--gray-9)")),
                                rx.switch(
                                    checked=State.is_expert_mode,
                                    on_change=State.toggle_mode,
                                    color_scheme="violet",
                                    size="3", cursor="pointer"
                                ),
                                rx.text("Mode Expert", weight="bold", 
                                        color=rx.cond(State.is_expert_mode, "var(--violet-9)", "var(--gray-9)")),
                                
                                spacing="4", 
                                padding="10px", 
                                border="1px solid var(--gray-4)", 
                                border_radius="full", 
                                margin_bottom="20px", 
                                align_items="center", 
                                background="white"
                            ),
                            width="100%"
                        ),

                        # B. CONTENU DYNAMIQUE
                        rx.cond(
                            State.is_expert_mode,
                            
                            # --- VUE EXPERT (Grille classique) ---
                            rx.grid(
                                # Colonne Gauche : Configuration
                                configuration_form(),

                                # Colonne Droite : Panier & Prix
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

                                    pricing_block(), # Version allégée (sans sélecteur user)
                                    
                                    # Spinner de chargement
                                    rx.cond(
                                        State.is_loading, 
                                        rx.center(rx.spinner(size="3"), width="100%", padding="2rem")
                                    ),
                                    width="100%", spacing="6"
                                ),
                                columns="2", spacing="8", width="100%"
                            ),
                            
                            # --- VUE ASSISTANT (Wizard) ---
                            rx.center(
                                wizard_block(),
                                width="100%",
                                padding_y="20px"
                            )
                        ),
                        
                        # C. CONSOLE DE DÉPLOIEMENT (Toujours visible en bas)
                        deploy_console(),
                        
                        width="100%", spacing="6"
                    ),
                    value="sim", padding_top="2rem",
                ),

                # ==================================================
                # ONGLET 2 : GOUVERNANCE & LOGS
                # ==================================================
                rx.tabs.content(
                    rx.vstack(
                        # A. Dashboard Graphique (Coûts cumulés)
                        governance_dashboard(),
                        
                        rx.divider(margin_y="20px"),
                        
                        # B. Tableau des Logs (Audit Trail)
                        audit_log_table(),
                        
                        spacing="6",
                        width="100%"
                    ),
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

# Configuration de l'App
app = rx.App(theme=rx.theme(appearance="light", accent_color="indigo", radius="large"))

# AJOUT CRUCIAL : On charge l'historique ET les logs d'audit au démarrage
app.add_page(
    index, 
    title="EcoArch V10 Platform", 
    on_load=[State.load_history, State.load_audit_logs]
)