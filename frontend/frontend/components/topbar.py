"""Composant TopBar pour la sélection utilisateur et session - Design Apple-like."""
import reflex as rx

from ..state import State


def user_topbar() -> rx.Component:
    """Barre supérieure avec sélection utilisateur et ID session."""
    return rx.box(
        rx.hstack(
            # Sélection utilisateur
            _user_selector(),
            rx.spacer(),
            # ID Session
            _session_selector(),
            width="100%",
            padding_x="24px",
            padding_y="10px",
            align="center",
        ),
        border_bottom="1px solid var(--gray-4)",
        background="var(--gray-1)",
        width="100%",
        position="sticky",
        top="0",
        z_index="50",
        backdrop_filter="blur(20px) saturate(180%)",
    )


def _user_selector() -> rx.Component:
    """Sélecteur d'utilisateur avec style Apple."""
    return rx.hstack(
        rx.box(
            rx.icon("user", size=14, color="var(--accent-11)"),
            background="var(--accent-3)",
            padding="6px",
            border_radius="8px",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.text(
            "Utilisateur",
            weight="medium",
            size="2",
            color="var(--gray-11)",
            letter_spacing="-0.01em",
        ),
        rx.select(
            State.users_list,
            value=State.current_user,
            on_change=State.set_user,
            size="2",
            variant="surface",
            radius="large",
            width="180px",
        ),
        align="center",
        spacing="3",
    )


def _session_selector() -> rx.Component:
    """Sélecteur d'ID de session avec style Apple."""
    return rx.hstack(
        rx.text(
            "Session",
            weight="medium",
            size="2",
            color="var(--gray-11)",
            letter_spacing="-0.01em",
        ),
        rx.box(
            rx.input(
                value=State.deployment_id,
                on_change=State.set_deployment_id,
                width="100px",
                size="2",
                variant="surface",
                font_family="'SF Mono', 'Fira Code', monospace",
                font_size="13px",
                letter_spacing="0.02em",
                radius="large",
            ),
            position="relative",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("refresh-cw", size=14),
                on_click=State.generate_new_id,
                size="2",
                variant="ghost",
                radius="full",
                cursor="pointer",
                color="var(--gray-11)",
                _hover={
                    "background": "var(--gray-4)",
                    "color": "var(--accent-11)",
                },
                transition="all 0.2s ease",
            ),
            content="Nouvelle Session",
        ),
        align="center",
        spacing="2",
    )