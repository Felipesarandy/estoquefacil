"""Registro das rotas do backend do EstoqueFácil."""

import os

from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.routes.common import error

jwt = JWTManager()


def configure_api(app, config_name=None):

    # Configuração da autenticação JWT
    jwt_key = os.getenv("JWT_SECRET_KEY") or app.config.get("SECRET_KEY")

    config_name = config_name or os.getenv(
        "FLASK_CONFIG", "development"
    )

    if not app.testing and config_name == "production":
        if (
            not os.getenv("SECRET_KEY")
            or os.getenv("SECRET_KEY") == "chave-padrao-insegura"
            or not os.getenv("JWT_SECRET_KEY")
        ):
            raise RuntimeError(
                "Configure SECRET_KEY e JWT_SECRET_KEY em produção"
            )

    app.config["JWT_SECRET_KEY"] = jwt_key
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", 3600)

    jwt.init_app(app)

    # Permite a comunicação com o frontend
    origins = [
        s.strip()
        for s in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if s.strip()
    ]

    CORS(app, resources={r"/api/*": {"origins": origins}})

    # Registro das rotas
    from app.routes import auth, users, catalog, stock

    for blueprint in (
        auth.bp,
        users.bp,
        catalog.bp,
        stock.bp
    ):
        app.register_blueprint(blueprint)

    # Tratamento de erros de autenticação
    @jwt.unauthorized_loader
    def missing_token(reason):
        return error("Token de acesso obrigatório", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error("Token inválido", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return error("Token expirado", 401)

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return error("Token revogado", 401)