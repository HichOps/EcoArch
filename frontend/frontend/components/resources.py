"""Composant Liste des ressources du panier."""
import reflex as rx

from ..state import State

# Mapping type -> icône
RESOURCE_ICONS = {
    "compute": "server",
    "sql": "database",
    "storage": "container",
}


def resource_item(item: dict, index: int) -> rx.Component:
    """Affiche un élément de ressource dans le panier."""
    icon = rx.cond(
        item["type"] == "compute",
        "server",
        rx.cond(item["type"] == "sql", "database", "container"),
    )
    
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=18, color=rx.color("indigo", 9)),
            rx.vstack(
                rx.text(
                    item["display_name"],
                    weight="bold",
                    size="2",
                    color=rx.color("slate", 12),
                ),
                rx.cond(
                    item["type"] == "compute",
                    rx.text(
                        f"{item['disk_size']} GB SSD",
                        size="1",
                        color=rx.color("slate", 10),
                    ),
                    rx.text(
                        "Ressource Gérée",
                        size="1",
                        color=rx.color("slate", 10),
                    ),
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("trash-2", size=16),
                on_click=lambda: State.remove_resource(index),
                variant="soft",
                color_scheme="ruby",
                size="1",
                cursor="pointer",
            ),
            align="center",
            width="100%",
            padding="12px",
            border_bottom=f"1px solid {rx.color('slate', 4)}",
        ),
        width="100%",
        background=rx.color("slate", 2),
        border_radius="8px",
        margin_bottom="8px",
        border=f"1px solid {rx.color('slate', 4)}",
    )


def resource_list_display() -> rx.Component:
    """Affiche la liste des ressources dans le panier."""
    return rx.vstack(
        rx.heading("Estimation", size="4", weight="bold"),
        rx.box(
            rx.vstack(
                rx.cond(
                    State.resource_list,
                    rx.foreach(
                        State.resource_list,
                        lambda item, idx: resource_item(item, idx),
                    ),
                    rx.center(
                        rx.text(
                            "Votre panier est vide",
                            color="gray",
                            font_style="italic",
                        ),
                        padding="20px",
                        width="100%",
                    ),
                ),
                width="100%",
                padding="10px",
            ),
            background=rx.color("slate", 2),
            border=f"1px solid {rx.color('slate', 4)}",
            border_radius="12px",
            box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            width="100%",
        ),
        width="100%",
    )