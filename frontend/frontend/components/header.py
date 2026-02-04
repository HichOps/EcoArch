"""Composant Header de l'application - Design Apple-like."""
import reflex as rx


def header() -> rx.Component:
    """Barre de navigation principale avec effet glass."""
    return rx.box(
        rx.container(
            rx.hstack(
                # Logo et titre
                rx.hstack(
                    rx.box(
                        rx.icon("leaf", color="white", size=18),
                        background="linear-gradient(135deg, #007AFF 0%, #5856D6 100%)",
                        padding="8px",
                        border_radius="12px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        box_shadow="0 4px 12px rgba(0, 122, 255, 0.3)",
                    ),
                    rx.vstack(
                        rx.heading(
                            "EcoArch",
                            size="5",
                            weight="bold",
                            letter_spacing="-0.03em",
                            line_height="1",
                        ),
                        rx.text(
                            "Cloud Architecture",
                            size="1",
                            color=rx.color("gray", 10),
                            weight="medium",
                            letter_spacing="0.02em",
                        ),
                        spacing="0",
                        align="start",
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.spacer(),
                # Toggle thème avec style Apple
                rx.box(
                    rx.color_mode.button(
                        size="2",
                        variant="ghost",
                        radius="full",
                    ),
                    padding="4px",
                    border_radius="var(--radius-full)",
                    background="var(--gray-3)",
                    _hover={
                        "background": "var(--gray-4)",
                    },
                    transition="all 0.2s ease",
                ),
                align="center",
            ),
            padding_y="12px",
            size="3",
        ),
        position="sticky",
        top="48px",
        z_index="40",
        backdrop_filter="blur(20px) saturate(180%)",
        background="var(--color-background-translucent)",
        border_bottom="1px solid var(--gray-4)",
        width="100%",
        transition="all 0.3s ease",
    )