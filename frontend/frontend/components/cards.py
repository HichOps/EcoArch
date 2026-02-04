"""Composants de cartes réutilisables - Design Apple-like."""
import reflex as rx


def card_container(child: rx.Component, class_name: str = "") -> rx.Component:
    """Conteneur de carte avec effet glass Apple-like."""
    return rx.box(
        child,
        background="var(--gray-1)",
        border="1px solid var(--gray-4)",
        box_shadow="0 2px 8px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04)",
        border_radius="20px",
        padding="28px",
        transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        _hover={
            "transform": "translateY(-2px)",
            "box_shadow": "0 8px 24px rgba(0, 0, 0, 0.08), 0 16px 32px rgba(0, 0, 0, 0.06)",
        },
        width="100%",
        class_name=class_name,
    )


def price_hero(
    cost: float,
    accent_color: str,
    icon_tag: str,
    label_text: str,
) -> rx.Component:
    """Affichage central du prix avec design Apple premium."""
    # Mapping des couleurs vers les couleurs Apple
    color_map = {
        "grass": "#34C759",
        "green": "#34C759",
        "ruby": "#FF3B30",
        "red": "#FF3B30",
    }
    actual_color = color_map.get(accent_color, "#007AFF")
    
    return card_container(
        rx.vstack(
            rx.text(
                "Estimation Mensuelle",
                size="1",
                weight="medium",
                color="var(--gray-10)",
                letter_spacing="0.08em",
                text_transform="uppercase",
            ),
            rx.hstack(
                rx.text(
                    "$",
                    font_size="28px",
                    weight="medium",
                    color="var(--gray-9)",
                    line_height="1",
                    padding_top="8px",
                ),
                rx.text(
                    f"{cost:.2f}",
                    font_size="56px",
                    weight="bold",
                    line_height="1",
                    letter_spacing="-0.03em",
                    color="var(--gray-12)",
                ),
                align="start",
                spacing="1",
            ),
            rx.box(
                rx.hstack(
                    rx.icon(icon_tag, size=14, color=actual_color),
                    rx.text(
                        label_text,
                        weight="bold",
                        size="2",
                        color=actual_color,
                    ),
                    spacing="2",
                    align="center",
                ),
                padding="8px 16px",
                border_radius="var(--radius-full)",
                background=f"color-mix(in srgb, {actual_color} 12%, transparent)",
            ),
            align="center",
            spacing="4",
            width="100%",
        ),
        class_name="animate-in",
    )


def stat_card(
    label: str,
    value: str,
    subtext: str,
    icon: str,
    color_scheme: str,
) -> rx.Component:
    """Carte KPI pour le dashboard de gouvernance - Style Apple."""
    # Mapping couleurs
    color_map = {
        "blue": "#007AFF",
        "green": "#34C759",
        "orange": "#FF9500",
        "purple": "#AF52DE",
        "red": "#FF3B30",
        "indigo": "#5856D6",
    }
    actual_color = color_map.get(color_scheme, "#007AFF")
    
    return card_container(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=16, color=actual_color),
                    background=f"color-mix(in srgb, {actual_color} 12%, transparent)",
                    padding="8px",
                    border_radius="10px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text(
                    label,
                    weight="medium",
                    size="2",
                    color="var(--gray-10)",
                    letter_spacing="-0.01em",
                ),
                align="center",
                spacing="3",
            ),
            rx.text(
                value,
                font_size="32px",
                weight="bold",
                color="var(--gray-12)",
                letter_spacing="-0.02em",
                line_height="1.1",
            ),
            rx.text(
                subtext,
                size="2",
                weight="medium",
                color=actual_color,
            ),
            align="start",
            spacing="3",
        ),
    )