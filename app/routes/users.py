
from flask import Blueprint, jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User
from app.routes.common import (
    authorized,
    body,
    error,
    required_string,
    serialize_user
)

# Rotas de gerenciamento dos usuarios
bp = Blueprint("users", __name__, url_prefix="/api/users")


# LISTAR FUNCIONARIOS
@bp.get("")
@authorized(admin=True)
def list_users(user):
    items = db.session.query(User).filter_by(
        store_id=user.store_id
    ).order_by(User.name).all()

    return jsonify([serialize_user(x) for x in items])


# CADASTRAR FUNCIONARIO
@bp.post("")
@authorized(admin=True)
def create_user(user):
    try:
        data = body()

        name = required_string(data, "name", 120)
        email = required_string(data, "email").lower()
        password = required_string(data, "password", 200)

        if "@" not in email or len(password) < 8:
            return error(
                "Informe e-mail valido e senha com pelo menos 8 caracteres"
            )

        new_user = User(
            store_id=user.store_id,
            name=name,
            email=email,
            role="funcionario",
            active=True
        )

        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify(serialize_user(new_user)), 201

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error("E-mail ja cadastrado", 409)


# EDITAR OU DESATIVAR FUNCIONARIO
@bp.patch("/<int:user_id>")
@authorized(admin=True)
def update_user(admin, user_id):

    target = db.session.query(User).filter_by(
        id=user_id,
        store_id=admin.store_id
    ).first()

    if target is None:
        return error("Funcionario nao encontrado", 404)

    try:
        data = body()

        if "name" in data:
            target.name = required_string(data, "name", 120)

        if "active" in data:
            if not isinstance(data["active"], bool):
                raise ValueError("active deve ser booleano")

            if target.id == admin.id and not data["active"]:
                return error(
                    "Voce nao pode desativar sua propria conta"
                )

            target.active = data["active"]

        db.session.commit()

        return jsonify(serialize_user(target))

    except ValueError as exc:
        return error(str(exc))
