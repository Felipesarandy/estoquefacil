
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Category, Supplier, Product
from app.routes.common import (
    authorized,
    body,
    decimal_field,
    error,
    integer_field,
    optional_string,
    required_string,
    scoped,
    serialize_category,
    serialize_supplier,
    serialize_product
)

# Blueprint de categorias, fornecedores e produtos
bp = Blueprint("catalog", __name__, url_prefix="/api")


# ==========================================
# CATEGORIAS
# ==========================================

@bp.get("/categories")
@authorized()
def categories(user):
    items = Category.query.filter_by(
        store_id=user.store_id
    ).order_by(Category.name).all()

    return jsonify([serialize_category(x) for x in items])


@bp.post("/categories")
@authorized(admin=True)
def create_category(user):
    try:
        data = body()
        cat = Category(
            store_id=user.store_id,
            name=required_string(data, "name", 80)
        )
        db.session.add(cat)
        db.session.commit()
        return jsonify(serialize_category(cat)), 201

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error("Categoria ja cadastrada", 409)


@bp.patch("/categories/<int:category_id>")
@authorized(admin=True)
def update_category(user, category_id):
    cat = scoped(Category, category_id, user)

    if cat is None:
        return error("Categoria nao encontrada", 404)

    try:
        data = body()
        cat.name = required_string(data, "name", 80)
        db.session.commit()
        return jsonify(serialize_category(cat))

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error("Categoria ja cadastrada", 409)


@bp.delete("/categories/<int:category_id>")
@authorized(admin=True)
def delete_category(user, category_id):
    cat = scoped(Category, category_id, user)

    if cat is None:
        return error("Categoria nao encontrada", 404)

    if Product.query.filter_by(
        store_id=user.store_id,
        category_id=cat.id
    ).first():
        return error("Categoria possui produtos", 409)

    db.session.delete(cat)
    db.session.commit()
    return "", 204


# ==========================================
# FORNECEDORES
# ==========================================

@bp.get("/suppliers")
@authorized()
def suppliers(user):
    items = Supplier.query.filter_by(
        store_id=user.store_id
    ).order_by(Supplier.name).all()

    return jsonify([serialize_supplier(x) for x in items])


@bp.post("/suppliers")
@authorized(admin=True)
def create_supplier(user):
    try:
        data = body()

        item = Supplier(
            store_id=user.store_id,
            name=required_string(data, "name", 120),
            phone=optional_string(data, "phone", 20),
            email=optional_string(data, "email", 255)
        )

        db.session.add(item)
        db.session.commit()
        return jsonify(serialize_supplier(item)), 201

    except ValueError as exc:
        return error(str(exc))


@bp.patch("/suppliers/<int:supplier_id>")
@authorized(admin=True)
def update_supplier(user, supplier_id):
    item = scoped(Supplier, supplier_id, user)

    if item is None:
        return error("Fornecedor nao encontrado", 404)

    try:
        data = body()

        if "name" in data:
            item.name = required_string(data, "name", 120)

        for field, limit in (
            ("phone", 20),
            ("email", 255)
        ):
            if field in data:
                setattr(
                    item, field,
                    optional_string(data, field, limit)
                )

        db.session.commit()
        return jsonify(serialize_supplier(item))

    except ValueError as exc:
        return error(str(exc))


@bp.delete("/suppliers/<int:supplier_id>")
@authorized(admin=True)
def delete_supplier(user, supplier_id):
    item = scoped(Supplier, supplier_id, user)

    if item is None:
        return error("Fornecedor nao encontrado", 404)

    if Product.query.filter_by(
        store_id=user.store_id,
        supplier_id=item.id
    ).first():
        return error("Fornecedor associado a produtos", 409)

    db.session.delete(item)
    db.session.commit()
    return "", 204


# ==========================================
# VALIDACAO DE PRODUTOS
# ==========================================

def validate_product(data, user, product=None):

    if product is None:
        product = Product(
            store_id=user.store_id,
            current_stock=0,
            active=True,
            cost_price=0,
            sale_price=0,
            min_stock=0,
            unit="un"
        )

    if "current_stock" in data:
        raise ValueError(
            "Saldo so pode ser alterado por movimentacoes"
        )

    if "name" in data or product.id is None:
        product.name = required_string(data, "name", 150)

    if "category_id" in data or product.id is None:
        category_id = integer_field(
            data, "category_id", required=True
        )

        if not scoped(Category, category_id, user):
            raise ValueError(
                "Categoria nao encontrada nesta loja"
            )

        product.category_id = category_id

    if "supplier_id" in data:
        supplier_id = integer_field(data, "supplier_id")

        if supplier_id and not scoped(
            Supplier, supplier_id, user
        ):
            raise ValueError(
                "Fornecedor nao encontrado nesta loja"
            )

        product.supplier_id = supplier_id

    if "code" in data:
        product.code = optional_string(data, "code", 50)

    if "unit" in data or product.id is None:
        unit = data.get("unit", "un")

        if unit not in ("un", "kg", "l", "m", "cx"):
            raise ValueError(
                "Unidade invalida: use un, kg, l, m ou cx"
            )

        product.unit = unit

    for field in (
        "cost_price",
        "sale_price",
        "min_stock",
        "max_stock"
    ):
        if field in data:
            if field == "max_stock" and data[field] is None:
                product.max_stock = None
            else:
                setattr(
                    product,
                    field,
                    decimal_field(
                        data,
                        field,
                        scale=2 if field.endswith("price") else 3
                    )
                )

    if "active" in data:
        if not isinstance(data["active"], bool):
            raise ValueError("active deve ser booleano")
        product.active = data["active"]

    if (
        product.max_stock is not None
        and product.max_stock < product.min_stock
    ):
        raise ValueError(
            "Estoque maximo nao pode ser menor que minimo"
        )

    return product


# ==========================================
# PRODUTOS
# ==========================================

@bp.get("/products")
@authorized()
def products(user):
    query = Product.query.filter_by(store_id=user.store_id)

    if request.args.get(
        "include_inactive", "false"
    ).lower() != "true":
        query = query.filter_by(active=True)

    search = request.args.get("search", "").strip()

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.code.ilike(f"%{search}%")
            )
        )

    if request.args.get("category_id"):
        try:
            category_id = int(request.args["category_id"])
        except ValueError:
            return error("category_id invalido")

        query = query.filter_by(category_id=category_id)

    items = query.order_by(Product.name).all()
    return jsonify([serialize_product(x) for x in items])


@bp.get("/products/<int:product_id>")
@authorized()
def get_product(user, product_id):
    item = scoped(Product, product_id, user)

    if item is None:
        return error("Produto nao encontrado", 404)

    return jsonify(serialize_product(item))


@bp.post("/products")
@authorized(admin=True)
def create_product(user):
    try:
        item = validate_product(body(), user)
        db.session.add(item)
        db.session.commit()

        return jsonify(serialize_product(item)), 201

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error(
            "Codigo de produto ja utilizado nesta loja", 409
        )


@bp.patch("/products/<int:product_id>")
@authorized(admin=True)
def update_product(user, product_id):
    item = scoped(Product, product_id, user)

    if item is None:
        return error("Produto nao encontrado", 404)

    try:
        data = body()
        item = validate_product(data, user, item)

        db.session.commit()
        return jsonify(serialize_product(item))

    except ValueError as exc:
        return error(str(exc))

    except IntegrityError:
        db.session.rollback()
        return error(
            "Codigo de produto ja utilizado nesta loja", 409
        )


@bp.delete("/products/<int:product_id>")
@authorized(admin=True)
def deactivate_product(user, product_id):
    item = scoped(Product, product_id, user)

    if item is None:
        return error("Produto nao encontrado", 404)

    item.active = False
    db.session.commit()

    return "", 204
