
"""Funções auxiliares do backend EstoqueFácil."""

from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import User


# Retorna mensagens de erro da API
def error(message, status=400):
    return jsonify({"error": message}), status


# Recebe os dados enviados em JSON
def body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ValueError("Envie um objeto JSON válido")

    return data


# Verifica campos de texto obrigatórios
def required_string(data, field, max_length=255):
    value = data.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Campo obrigatório: {field}")

    value = value.strip()

    if len(value) > max_length:
        raise ValueError(f"{field} deve ter no máximo {max_length} caracteres")

    return value


# Verifica campos de texto opcionais
def optional_string(data, field, max_length=255):
    value = data.get(field)

    if value is None or value == "":
        return None

    if not isinstance(value, str) or len(value.strip()) > max_length:
        raise ValueError(f"{field} inválido")

    return value.strip()


# Valida valores numéricos
def decimal_field(data, field, default=None, positive=False, scale=3):
    value = data.get(field, default)

    if value is None or isinstance(value, bool):
        raise ValueError(f"{field} deve ser numérico")

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} deve ser numérico") from None

    if not number.is_finite():
        raise ValueError(f"{field} inválido")

    if positive and number <= 0:
        raise ValueError(f"{field} deve ser maior que zero")

    if not positive and number < 0:
        raise ValueError(f"{field} não pode ser negativo")

    if number.as_tuple().exponent < -scale:
        raise ValueError(f"{field} possui casas decimais demais")

    if number >= Decimal(10) ** (10 - scale):
        raise ValueError(f"{field} fora do limite permitido")

    return number


# Valida identificadores numéricos
def integer_field(data, field, required=False):
    value = data.get(field)

    if value is None and not required:
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} deve ser um ID inteiro positivo")

    return value


# Controla as permissões dos usuários
def authorized(admin=False):
    def decorator(fn):

        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            try:
                user = db.session.get(User, int(get_jwt_identity()))
            except (ValueError, TypeError):
                user = None

            if user is None or not user.active:
                return error("Usuário inativo ou inexistente", 401)

            if admin and user.role != "admin":
                return error("Acesso permitido somente ao administrador", 403)

            return fn(user, *args, **kwargs)

        return wrapped

    return decorator


# Garante que os dados pertencem à loja do usuário
def scoped(model, entity_id, user):
    return db.session.query(model).filter_by(
        id=entity_id,
        store_id=user.store_id
    ).first()


# Formata datas
def as_date(value):
    return value.isoformat() if value else None


# Converte usuários em JSON
def serialize_user(user):
    return {
        "id": user.id,
        "store_id": user.store_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active
    }


# Converte categorias em JSON
def serialize_category(item):
    return {
        "id": item.id,
        "name": item.name
    }


# Converte fornecedores em JSON
def serialize_supplier(item):
    return {
        "id": item.id,
        "name": item.name,
        "phone": item.phone,
        "email": item.email
    }


# Converte produtos em JSON
def serialize_product(item):
    return {
        "id": item.id,
        "name": item.name,
        "code": item.code,
        "category_id": item.category_id,
        "supplier_id": item.supplier_id,
        "unit": item.unit,
        "cost_price": str(item.cost_price),
        "sale_price": str(item.sale_price),
        "min_stock": str(item.min_stock),
        "max_stock": str(item.max_stock) if item.max_stock is not None else None,
        "current_stock": str(item.current_stock),
        "stock_value": str(item.stock_value),
        "is_low_stock": item.is_low_stock,
        "active": item.active
    }


# Converte movimentações de estoque em JSON
def serialize_movement(item):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "user_id": item.user_id,
        "type": item.type,
        "reason": item.reason,
        "quantity": str(item.quantity),
        "unit_cost": str(item.unit_cost),
        "total_cost": str(item.total_cost),
        "note": item.note,
        "created_at": as_date(item.created_at)
    }
