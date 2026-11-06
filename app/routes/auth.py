
from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Store, User
from app.routes.common import (
    authorized,
    body,
    error,
    optional_string,
    required_string,
    serialize_user
)

# Cria as rotas de autenticacao
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# CADASTRO DE LOJA E ADMINISTRADOR
@bp.post("/register")
def register():
    try:
        data = body()

        store_name = required_string(data, "store_name", 120)
        name = required_string(data, "name", 120)
        email = required_string(data, "email", 255).lower()
        password = required_string(data, "password", 200)
        business_type = optional_string(data, "business_type", 80)

        if "@" not in email or len(password) < 8:
            return error(
                "Informe e-mail valido e senha com pelo menos 8 caracteres"
            )

        store = Store(
            name=store_name,
            business_type=business_type
        )

        user = User(
            store=store,
            name=name,
            email=email,
            role="admin",
            active=True
        )

        user.set_password(password)

        db.session.add_all([store, user])
        db.session.commit()

        return jsonify({
            "store": {
                "id": store.id,
                "name": store.name
            },
            "user": serialize_user(user)
        }), 201

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error("E-mail ja cadastrado", 409)


# LOGIN DO USUARIO
@bp.post("/login")
def login():
    try:
        data = body()

        email = required_string(data, "email").lower()
        password = required_string(data, "password")

    except ValueError as exc:
        return error(str(exc))

    user = db.session.query(User).filter_by(
        email=email,
        active=True
    ).first()

    if user is None or not user.check_password(password):
        return error("Credenciais invalidas", 401)

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "user": serialize_user(user)
    }), 200


# CONSULTAR USUARIO LOGADO
@bp.get("/me")
@authorized()
def me(user):
    return jsonify(serialize_user(user))
