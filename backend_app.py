
"""Backend do EstoqueFácil, sem modificar o código original."""

from app import create_app as create_original_app
from app.routes import configure_api


def create_app(config_name=None):
    app = create_original_app(config_name)
    configure_api(app, config_name=config_name)
    return app
