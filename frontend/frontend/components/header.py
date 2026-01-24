import reflex as rx

def header():
    return rx.box(
        rx.container(
            rx.hstack(
                rx.hstack(
                    rx.icon("leaf", color=rx.color("indigo", 9), size=24),
                    rx.heading("EcoArch", size="6", weight="bold", letter_spacing="-0.5px"),
                    rx.text("V9 Modular", size="6", color=rx.color("slate", 10)),
                    spacing="2", align="center"
                ),
                rx.spacer(),
                rx.color_mode.button(size="2", variant="soft"),
                align="center",
            ),
            padding_y="4",
        ),
        position="sticky", top="0", z_index="50",
        backdrop_filter="blur(16px)",
        border_bottom=f"1px solid {rx.color('slate', 4)}",
        width="100%",
        background=rx.color("slate", 1, alpha=True),
    )