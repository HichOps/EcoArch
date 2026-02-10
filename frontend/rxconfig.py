import reflex as rx
import os

config = rx.Config(
    app_name="frontend",
    api_url=os.getenv(
        "API_URL",
        "https://ecoarch-app-514436528658.us-central1.run.app",
    ),
)