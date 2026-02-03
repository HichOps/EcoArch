"""Composant Dashboard de gouvernance et audit."""
import reflex as rx

from ..state import State


def audit_row(row: dict) -> rx.Component:
    """Ligne du tableau d'audit."""
    return rx.table.row(
        rx.table.cell(row["formatted_date"], font_size="13px"),
        rx.table.cell(row["user"], font_size="13px", weight="bold"),
        rx.table.cell(rx.badge(row["action"], color_scheme="gray")),
        rx.table.cell(
            rx.text(
                row["resources_summary"],
                font_size="11px",
                max_width="300px",
                truncate=True,
            ),
        ),
        rx.table.cell(rx.text(row["formatted_cost"], font_family="monospace")),
        rx.table.cell(
            rx.badge(
                row["status"],
                color_scheme=rx.cond(
                    row["status"] == "SUCCESS",
                    "green",
                    rx.cond(row["status"] == "PENDING", "yellow", "red"),
                ),
                variant="solid",
            ),
        ),
    )


def governance_dashboard() -> rx.Component:
    """Dashboard de gouvernance avec journal d'audit."""
    return rx.vstack(
        # En-tête
        rx.hstack(
            rx.icon("file-text", size=28),
            rx.heading("Journal d'Audit Officiel", size="6"),
            align="center",
            spacing="3",
        ),
        rx.text(
            "Historique immuable des déploiements et destructions.",
            color="gray",
        ),
        rx.divider(margin_y="15px"),
        
        # Bouton refresh
        rx.hstack(
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=16),
                "Actualiser",
                on_click=State.load_audit_logs,
                size="2",
                variant="surface",
            ),
            width="100%",
            margin_bottom="10px",
        ),
        
        # Tableau d'audit
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Utilisateur"),
                        rx.table.column_header_cell("Action"),
                        rx.table.column_header_cell("Détail"),
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
            border="1px solid var(--gray-4)",
            border_radius="8px",
            overflow="auto",
            max_height="600px",
        ),
        width="100%",
        spacing="4",
        padding="20px",
        background="white",
        border_radius="12px",
    )