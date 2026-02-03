"""Composant TopBar pour la sélection utilisateur et session."""
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
            padding_x="20px",
            padding_y="12px",
            align="center",
        ),
        border_bottom="1px solid var(--gray-4)",
        background="white",
        width="100%",
        position="sticky",
        top="0",
        z_index="10",
    )


def _user_selector() -> rx.Component:
    """Sélecteur d'utilisateur."""
    return rx.hstack(
        rx.icon("circle-user", size=20, color="var(--violet-9)"),
        rx.text("Utilisateur:", weight="bold", size="2", color="gray"),
        rx.select(
            State.users_list,
            value=State.current_user,
            on_change=State.set_user,
            size="2",
            variant="soft",
            color_scheme="violet",
            radius="full",
            width="200px",
        ),
        align="center",
        spacing="2",
    )


def _session_selector() -> rx.Component:
    """Sélecteur d'ID de session."""
    return rx.hstack(
        rx.text("ID Session:", weight="bold", size="2", color="gray"),
        rx.input(
            value=State.deployment_id,
            on_change=State.set_deployment_id,
            width="120px",
            size="2",
            variant="soft",
            font_family="monospace",
        ),
        rx.icon_button(
            rx.icon("refresh-cw", size=16),
            on_click=State.generate_new_id,
            size="2",
            variant="ghost",
            color_scheme="gray",
            title="Nouvelle Session",
        ),
        align="center",
        spacing="2",
    )