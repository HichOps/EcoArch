import reflex as rx
from ..state import State

def stat_card(label: str, value: str, icon: str, color: str):
    return rx.card(
        rx.hstack(
            rx.icon(icon, color=color, size=24),
            rx.vstack(
                rx.text(label, size="1", color="gray"),
                rx.text(value, size="4", weight="bold"),
                spacing="1"
            ),
            align="center", spacing="3"
        ),
        size="2"
    )

def history_table():
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Date"),
                rx.table.column_header_cell("Coût Mensuel"),
                rx.table.column_header_cell("Statut"),
            )
        ),
        rx.table.body(
            rx.foreach(
                State.history,
                lambda row: rx.table.row(
                    rx.table.cell(row["display_date"]),
                    rx.table.cell(f"${row['total_monthly_cost']}"),
                    rx.table.cell(
                        rx.badge(
                            row["status"],
                            color_scheme=rx.cond(row["status"] == "PASSED", "green", "red")
                        )
                    ),
                )
            )
        ),
        width="100%"
    )

def governance_dashboard():
    return rx.vstack(
        rx.heading("Tableau de Bord Gouvernance", size="6"),
        rx.divider(),
        
        # KPI ROW (Cartes indicateurs)
        rx.grid(
            stat_card("Dernier Coût", State.last_run_cost, "dollar-sign", "blue"),
            stat_card("Conformité", State.last_run_status, "shield-check", State.last_run_color),
            columns="2", spacing="4", width="100%"
        ),
        
        # HISTORY TABLE (Historique Supabase)
        rx.box(
            rx.text("Historique des Simulations", weight="bold", margin_bottom="10px"),
            rx.card(
                history_table(),
                width="100%"
            ),
            width="100%"
        ),
        spacing="6", width="100%"
    )