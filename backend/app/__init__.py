import os

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import config
from app.extensions import db, migrate


# O SQLite só verifica chaves estrangeiras com este PRAGMA ligado
@event.listens_for(Engine, "connect")
def _sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    from app import models  # noqa: F401  (registra os models para o Flask-Migrate)
    from app.seed import seed_command
    app.cli.add_command(seed_command)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
