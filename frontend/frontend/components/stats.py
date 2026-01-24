import reflex as rx
from ..state import State

def stat_card(title, value, subtitle, icon, color):
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, color=rx.color(color, 9), size=20),
                rx.text(title, size="2", weight="bold", color=rx.color("slate", 11)),
                align="center", spacing="2"
            ),
            rx.heading(value, size="6", weight="bold", color=rx.color("slate", 12)),
            rx.text(subtitle, size="1", color=rx.color("slate", 10)),
            spacing="1"
        ),
        padding="16px",
        background=rx.color("slate", 2),
        border=f"1px solid {rx.color('slate', 4)}",
        border_radius="8px"
    )

def governance_dashboard():
    return rx.vstack(
        rx.heading("Dashboard FinOps", size="6", weight="bold", margin_bottom="1rem"),
        rx.grid(
            stat_card("Dernier Coût", State.last_run_cost, "Pipeline", "dollar-sign", "indigo"),
            stat_card("Statut", State.last_run_status, "Conformité", "shield-check", State.last_run_color),
            stat_card("Budget", "50.00 $", "Limite", "target", "gray"),
            columns="3", spacing="4", width="100%"
        ),
        rx.box(
             rx.vstack(
                rx.text("Historique", weight="bold", size="3"),
                rx.recharts.area_chart(
                    rx.recharts.area(
                        data_key="total_monthly_cost", 
                        stroke="#8884d8", fill="#8884d8",
                        is_animation_active=False
                    ),
                    rx.recharts.x_axis(data_key="display_date"),
                    rx.recharts.y_axis(),
                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                    data=State.history,
                    height=300, width="100%",
                ),
                width="100%", padding="20px"
             ),
             background=rx.color("slate", 2), 
             border=f"1px solid {rx.color('slate', 4)}",
             border_radius="12px", width="100%"
        ),
        
        # TABLEAU
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Auteur"),
                        rx.table.column_header_cell("Branche"),
                        rx.table.column_header_cell("Coût"),
                        rx.table.column_header_cell("Statut"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        State.history,
                        lambda item: rx.table.row(
                            rx.table.cell(item["display_date"]),
                            rx.table.cell(item["author"]),
                            rx.table.cell(item["branch_name"]),
                            rx.table.cell(f"{item['total_monthly_cost']} $", font_weight="bold"),
                            rx.table.cell(rx.badge(item["status"], variant="solid", color_scheme=rx.cond(item["status"] == "PASSED", "green", "red"))),
                        )
                    )
                ),
                variant="surface", width="100%",
            ),
            border_radius="12px", overflow="hidden", width="100%",
            border=f"1px solid {rx.color('slate', 4)}"
        ),
        spacing="6", width="100%",
    )