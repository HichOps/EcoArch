"""Composant Vue d'audit alternative (non utilisé actuellement)."""
import reflex as rx

from ..state import State


def status_badge(status: str) -> rx.Component:
    """Badge coloré selon le statut."""
    return rx.badge(
        status,
        color_scheme=rx.cond(
            status == "SUCCESS",
            "green",
            rx.cond(status == "ERROR", "red", "orange"),
        ),
        variant="solid",
        radius="full",
    )


def audit_row(row: dict) -> rx.Component:
    """Ligne du tableau d'audit."""
    return rx.table.row(
        rx.table.cell(row["id"], font_family="monospace"),
        rx.table.cell(row["formatted_date"], font_size="12px", color="gray"),
        rx.table.cell(
            rx.hstack(
                rx.icon("circle-user", size=16),
                rx.text(row["user"], weight="bold"),
                spacing="2",
                align="center",
            ),
        ),
        rx.table.cell(
            rx.badge(row["action"], variant="outline", color_scheme="gray"),
        ),
        rx.table.cell(
            rx.text(
                row["resources_summary"],
                font_size="12px",
                max_width="300px",
                truncate=True,
            ),
        ),
        rx.table.cell(
            rx.text(row["formatted_cost"], font_family="monospace", weight="bold"),
        ),
        rx.table.cell(status_badge(row["status"])),
    )


def audit_log_table() -> rx.Component:
    """Tableau complet des logs d'audit."""
    return rx.vstack(
        # En-tête
        rx.hstack(
            rx.vstack(
                rx.heading("Journal d'Audit", size="5"),
                rx.text(
                    "Historique immuable des opérations d'infrastructure.",
                    color="gray",
                    size="2",
                ),
                spacing="1",
            ),
            rx.spacer(),
            rx.button(
                rx.hstack(
                    rx.icon("refresh-cw", size=16),
                    rx.text("Actualiser"),
                ),
                on_click=State.load_audit_logs,
                size="2",
                variant="surface",
                color_scheme="gray",
            ),
            width="100%",
            align="center",
            margin_bottom="15px",
        ),
        
        # Tableau
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("ID"),
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Utilisateur"),
                        rx.table.column_header_cell("Action"),
                        rx.table.column_header_cell("Ressources"),
                        rx.table.column_header_cell("Coût"),
                        rx.table.column_header_cell("Statut"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(State.audit_logs, audit_row),
                ),
                variant="surface",
                size="2",
            ),
            width="100%",
            overflow="auto",
            max_height="600px",
            border="1px solid var(--gray-4)",
            border_radius="8px",
        ),
        
        width="100%",
        padding="20px",
        background="white",
        border_radius="12px",
        box_shadow="0 2px 10px rgba(0,0,0,0.05)",
    )