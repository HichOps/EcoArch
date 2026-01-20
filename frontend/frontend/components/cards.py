import reflex as rx

def card_container(child, bg_color="white"):
    """Un conteneur générique avec style 'Glass' et ombre douce"""
    return rx.box(
        child,
        bg=bg_color,
        backdrop_filter="blur(10px)",
        border="1px solid rgba(255, 255, 255, 0.6)",
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
        border_radius="24px",
        padding="32px",
        transition="all 0.2s ease-in-out",
        _hover={
            "transform": "translateY(-4px)",
            "box_shadow": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        },
        width="100%",
    )

def price_hero(cost: float, accent_color: str, icon_tag: str, label_text: str):
    """L'affichage central du prix avec un design premium"""
    return card_container(
        rx.vstack(
            rx.text(
                "Estimation Mensuelle", 
                size="2", 
                weight="bold", 
                color=rx.color("slate", 10), 
                letter_spacing="1px", 
                text_transform="uppercase"
            ),
            rx.hstack(
                rx.text("$", size="8", weight="medium", color=rx.color("slate", 9), padding_top="1rem"),
                rx.text(
                    f"{cost:.2f}", 
                    size="9", 
                    weight="bold", 
                    line_height="1", 
                    letter_spacing="-2px", 
                    color=rx.color("slate", 12)
                ),
                align="start",
                spacing="1"
            ),
            rx.badge(
                rx.icon(icon_tag, size=16),
                rx.text(label_text, weight="bold"),
                color_scheme=accent_color,
                variant="surface",
                size="3",
                radius="full",
                padding="0.5rem 1.5rem",
            ),
            align="center",
            spacing="5",
            width="100%"
        ),
        bg_color="rgba(255, 255, 255, 0.8)"
    )

def stat_card(label: str, value: str, subtext: str, icon: str, color_scheme: str):
    """Carte KPI pour le Dashboard de Gouvernance"""
    return card_container(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color=rx.color(color_scheme, 9)),
                rx.text(label, weight="bold", size="2", color=rx.color("slate", 10)),
                align="center",
                spacing="2"
            ),
            rx.text(value, size="7", weight="bold", color=rx.color("slate", 12)),
            rx.text(subtext, size="2", weight="medium", color=rx.color(color_scheme, 10)),
            align="start",
            spacing="3"
        ),
        bg_color="white"
    )