"""Composant Liste des ressources du panier - Design Apple-like."""
import reflex as rx

from ..state import State

# Mapping type -> icône et couleur
RESOURCE_CONFIG = {
    "compute": {"icon": "server", "color": "#007AFF"},
    "sql": {"icon": "database", "color": "#AF52DE"},
    "storage": {"icon": "folder", "color": "#FF9500"},
}


def resource_item(item: dict, index: int) -> rx.Component:
    """Affiche un élément de ressource dans le panier avec design Apple."""
    icon = rx.cond(
        item["type"] == "compute",
        "server",
        rx.cond(item["type"] == "sql", "database", "folder"),
    )
    
    color = rx.cond(
        item["type"] == "compute",
        "#007AFF",
        rx.cond(item["type"] == "sql", "#AF52DE", "#FF9500"),
    )
    
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=16, color=color),
                background=f"color-mix(in srgb, {color} 12%, transparent)",
                padding="10px",
                border_radius="12px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(
                    item["display_name"],
                    weight="bold",
                    size="2",
                    color="var(--gray-12)",
                    letter_spacing="-0.01em",
                ),
                rx.cond(
                    item["type"] == "compute",
                    rx.text(
                        f"{item['disk_size']} GB SSD",
                        size="1",
                        color="var(--gray-10)",
                    ),
                    rx.text(
                        "Ressource Gérée",
                        size="1",
                        color="var(--gray-10)",
                    ),
                ),
                align="start",
                spacing="0",
            ),
            rx.spacer(),
            rx.tooltip(
                rx.icon_button(
                    rx.icon("x", size=14),
                    on_click=lambda: State.remove_resource(index),
                    variant="ghost",
                    size="1",
                    radius="full",
                    cursor="pointer",
                    color="var(--gray-9)",
                    _hover={
                        "background": "var(--red-3)",
                        "color": "#FF3B30",
                    },
                    transition="all 0.15s ease",
                ),
                content="Supprimer",
            ),
            align="center",
            width="100%",
            padding="14px 16px",
        ),
        width="100%",
        background="var(--gray-1)",
        border_radius="14px",
        margin_bottom="8px",
        border="1px solid var(--gray-4)",
        transition="all 0.2s ease",
        _hover={
            "background": "var(--gray-2)",
            "border_color": "var(--gray-5)",
        },
    )


def resource_list_display() -> rx.Component:
    """Affiche la liste des ressources dans le panier avec design Apple."""
    return rx.vstack(
        rx.hstack(
            rx.box(
                rx.icon("shopping-cart", size=16, color="var(--accent-11)"),
                background="var(--accent-3)",
                padding="8px",
                border_radius="10px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.heading(
                "Panier",
                size="4",
                weight="bold",
                letter_spacing="-0.02em",
            ),
            rx.spacer(),
            rx.cond(
                State.resource_list,
                rx.box(
                    rx.text(
                        f"{rx.Var.create(State.resource_list).length()} ressource(s)",
                        size="1",
                        weight="medium",
                        color="var(--accent-11)",
                    ),
                    background="var(--accent-3)",
                    padding="4px 10px",
                    border_radius="var(--radius-full)",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.cond(
                    State.resource_list,
                    rx.foreach(
                        State.resource_list,
                        lambda item, idx: resource_item(item, idx),
                    ),
                    rx.center(
                        rx.vstack(
                            rx.box(
                                rx.icon("package", size=32, color="var(--gray-8)"),
                                padding="16px",
                                background="var(--gray-3)",
                                border_radius="16px",
                            ),
                            rx.text(
                                "Votre panier est vide",
                                color="var(--gray-10)",
                                weight="medium",
                                size="2",
                            ),
                            rx.text(
                                "Ajoutez des ressources pour commencer",
                                color="var(--gray-9)",
                                size="1",
                            ),
                            align="center",
                            spacing="3",
                        ),
                        padding="40px",
                        width="100%",
                    ),
                ),
                width="100%",
                padding="12px",
            ),
            background="var(--gray-2)",
            border="1px solid var(--gray-4)",
            border_radius="16px",
            box_shadow="0 2px 8px rgba(0, 0, 0, 0.04)",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )