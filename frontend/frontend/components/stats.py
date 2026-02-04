"""Composant Dashboard de gouvernance et audit - Design Apple-like."""
import reflex as rx

from ..state import State


def audit_row(row: dict) -> rx.Component:
    """Ligne du tableau d'audit avec style Apple."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                row["formatted_date"],
                font_size="13px",
                color="var(--gray-11)",
                font_family="'SF Mono', monospace",
            ),
        ),
        rx.table.cell(
            rx.text(
                row["user"],
                font_size="13px",
                weight="bold",
                color="var(--gray-12)",
            ),
        ),
        rx.table.cell(
            rx.box(
                rx.text(
                    row["action"],
                    size="1",
                    weight="medium",
                    color=rx.cond(
                        row["action"] == "DEPLOY",
                        "#007AFF",
                        "#FF9500",
                    ),
                ),
                padding="4px 10px",
                border_radius="var(--radius-full)",
                background=rx.cond(
                    row["action"] == "DEPLOY",
                    "color-mix(in srgb, #007AFF 12%, transparent)",
                    "color-mix(in srgb, #FF9500 12%, transparent)",
                ),
            ),
        ),
        rx.table.cell(
            rx.text(
                row["resources_summary"],
                font_size="12px",
                max_width="280px",
                truncate=True,
                color="var(--gray-10)",
            ),
        ),
        rx.table.cell(
            rx.text(
                row["formatted_cost"],
                font_family="'SF Mono', monospace",
                font_size="13px",
                weight="bold",
                color="var(--gray-12)",
            ),
        ),
        rx.table.cell(
            rx.box(
                rx.text(
                    row["status"],
                    size="1",
                    weight="bold",
                    color=rx.cond(
                        row["status"] == "SUCCESS",
                        "#34C759",
                        rx.cond(row["status"] == "PENDING", "#FF9500", "#FF3B30"),
                    ),
                ),
                padding="4px 10px",
                border_radius="var(--radius-full)",
                background=rx.cond(
                    row["status"] == "SUCCESS",
                    "color-mix(in srgb, #34C759 12%, transparent)",
                    rx.cond(
                        row["status"] == "PENDING",
                        "color-mix(in srgb, #FF9500 12%, transparent)",
                        "color-mix(in srgb, #FF3B30 12%, transparent)",
                    ),
                ),
            ),
        ),
        _hover={
            "background": "var(--gray-2)",
        },
        transition="background 0.15s ease",
    )


def governance_dashboard() -> rx.Component:
    """Dashboard de gouvernance avec journal d'audit - Style Apple."""
    return rx.vstack(
        # En-tête
        rx.hstack(
            rx.box(
                rx.icon("scroll-text", size=20, color="white"),
                background="linear-gradient(135deg, #5856D6 0%, #AF52DE 100%)",
                padding="12px",
                border_radius="14px",
                box_shadow="0 4px 12px rgba(88, 86, 214, 0.3)",
            ),
            rx.vstack(
                rx.heading(
                    "Journal d'Audit",
                    size="6",
                    weight="bold",
                    letter_spacing="-0.03em",
                ),
                rx.text(
                    "Historique immuable des déploiements",
                    color="var(--gray-10)",
                    size="2",
                    weight="medium",
                ),
                spacing="1",
                align="start",
            ),
            align="center",
            spacing="4",
        ),
        
        rx.box(height="20px"),
        
        # Bouton refresh avec style Apple
        rx.hstack(
            rx.spacer(),
            rx.button(
                rx.hstack(
                    rx.icon("refresh-cw", size=14),
                    rx.text("Actualiser", weight="medium"),
                    spacing="2",
                    align="center",
                ),
                on_click=State.load_audit_logs,
                size="2",
                variant="surface",
                radius="large",
                cursor="pointer",
                _active={
                    "transform": "scale(0.98)",
                },
            ),
            width="100%",
            margin_bottom="16px",
        ),
        
        # Tableau d'audit avec style Apple
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            rx.text("Date", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Utilisateur", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Action", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Détail", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Coût", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        rx.table.column_header_cell(
                            rx.text("Statut", weight="bold", size="2", color="var(--gray-11)"),
                        ),
                        background="var(--gray-2)",
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
            border_radius="14px",
            overflow="hidden",
            max_height="600px",
            box_shadow="0 2px 8px rgba(0, 0, 0, 0.04)",
        ),
        width="100%",
        spacing="3",
        padding="28px",
        background="var(--gray-1)",
        border_radius="20px",
        border="1px solid var(--gray-4)",
        class_name="animate-in",
    )