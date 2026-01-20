import reflex as rx

config = rx.Config(
    app_name="frontend",
    # Windows redirigera localhost:8000 vers votre WSL
    api_url="http://localhost:8000",
    telemetry_enabled=False,
)