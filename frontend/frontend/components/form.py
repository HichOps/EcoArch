import reflex as rx
from ..state import State

def configuration_form():
    return rx.box(
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
                background=rx.color("slate", 2),
                border=f"1px solid {rx.color('slate', 4)}",
                border_radius="12px",
                box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                width="100%"
            ),
            width="100%"
        )
    )