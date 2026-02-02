import reflex as rx
from ..state import State

def wizard_block():
    return rx.center(
        rx.vstack(
            rx.icon("bot", size=48, color="var(--violet-9)"),
            rx.heading("Architecte FinOps HA", size="6"),
            rx.text("Conception d'infra haute disponibilité & résiliente.", opacity=0.7),
            
            rx.divider(margin_y="20px", width="100%"),

            # Q1 : ENVIRONNEMENT (Dev vs Prod)
            rx.vstack(
                rx.text("1. Environnement cible", weight="bold"),
                rx.radio(
                    ["Développement (Dev)", "Production (Live)"],
                    default_value="Développement (Dev)",
                    on_change=State.set_wizard_env_logic,
                    direction="row", spacing="4"
                ),
                align="start", width="100%"
            ),

            rx.divider(margin_y="15px", opacity="0.3"),

            # Q2 : TRAFIC (Dimensionnement)
            rx.vstack(
                rx.text("2. Volume de trafic attendu", weight="bold"),
                rx.radio(
                    ["Faible (< 1k visiteurs/jour)", "Moyen (10k+)", "Élevé (Viral)"],
                    default_value="Faible (< 1k visiteurs/jour)",
                    on_change=State.set_wizard_traffic_logic,
                    direction="row", spacing="4"
                ),
                align="start", width="100%"
            ),

            rx.divider(margin_y="15px", opacity="0.3"),

            # Q3 : NATURE DE LA CHARGE (Optimisation Machine)
            # Cette question n'était pas là avant !
            rx.vstack(
                rx.text("3. Profil technique de l'application", weight="bold"),
                rx.radio(
                    ["Général (Web Server)", "Calcul Intensif (CPU)", "Mémoire Intensive (Cache/Data)"],
                    default_value="Général (Web Server)",
                    on_change=State.set_wizard_workload_logic,
                    direction="row", spacing="4"
                ),
                align="start", width="100%"
            ),

            rx.divider(margin_y="15px", opacity="0.3"),

            # Q4 : CRITICITÉ / SLA (Load Balancing & HA)
            # Cette question active le Load Balancer si "Critique"
            rx.vstack(
                rx.text("4. Niveau de service (SLA)", weight="bold"),
                rx.radio(
                    ["Standard (Redémarrage toléré)", "Critique (Haute Disponibilité)"],
                    default_value="Standard (Redémarrage toléré)",
                    on_change=State.set_wizard_criticality_logic,
                    direction="row", spacing="4"
                ),
                align="start", width="100%"
            ),

            rx.divider(margin_y="20px", width="100%"),

            # OPTION AUTO-DÉPLOIEMENT
            rx.box(
                rx.checkbox(
                    "Déployer automatiquement si le budget est respecté",
                    on_change=State.set_wizard_auto_deploy,
                    color_scheme="violet"
                ),
                padding="10px",
                border="1px dashed var(--violet-6)",
                border_radius="8px",
                width="100%",
                background="var(--violet-2)"
            ),

            rx.button(
                rx.hstack(rx.icon("sparkles", size=18), rx.text("GÉNÉRER & ESTIMER")),
                on_click=State.apply_recommendation_flow,
                size="4",
                width="100%",
                color_scheme="violet",
                variant="solid",
                cursor="pointer",
                margin_top="15px"
            )
        ),
        padding="40px",
        border="1px solid rgba(255,255,255,0.1)",
        border_radius="16px",
        background="var(--gray-2)",
        width="100%",
        max_width="700px" 
    )