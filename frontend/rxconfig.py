import reflex as rx
import os

api_url = os.getenv("API_URL", "http://localhost:8000")

config = rx.Config(
    app_name="frontend",
    api_url=api_url,
    telemetry_enabled=False,
    # Ajoutez cette ligne pour faire taire le warning dans les logs Docker
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)