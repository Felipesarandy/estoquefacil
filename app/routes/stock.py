
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request
from sqlalchemy import func, update

from app.extensions import db
from app.models import (
    InventoryCount,
    MOTIVOS_ENTRADA,
    MOTIVOS_SAIDA,
    Product,
    StockMovement
)
from app.routes.common import (
    authorized,
    as_date,
    body,
    decimal_field,
    error,
    integer_field,
    optional_string,
    scoped,
    serialize_movement,
    serialize_product
)


# Registro das rotas de estoque
bp = Blueprint("stock", __name__, url_prefix="/api")


# ==========================================
# REGISTRAR ENTRADAS E SAIDAS
# ==========================================

@bp.post("/movements")
@authorized()
def create_movement(user):
    try:
        data = body()

        product_id = integer_field(
            data, "product_id", required=True
        )

        item = scoped(Product, product_id, user)

        if item is None or not item.active:
            return error("Produto ativo nao encontrado", 404)

        kind = data.get("type")
        reason = data.get("reason")

        if kind not in ("entrada", "saida"):
            raise ValueError(
                "type deve ser entrada ou saida"
            )

        allowed = (
            MOTIVOS_ENTRADA
            if kind == "entrada"
            else MOTIVOS_SAIDA
        )

        if reason not in allowed:
            raise ValueError(
                f"Motivo invalido para {kind}"
            )

        quantity = decimal_field(
            data, "quantity", positive=True
        )

        note = optional_string(data, "note", 5000)

        # Saida: bloqueia saldo insuficiente.
        # Atualizacao e historico na mesma transacao.
        if kind == "saida":
            result = db.session.execute(
                update(Product)
                .where(
                    Product.id == item.id,
                    Product.store_id == user.store_id,
                    Product.active.is_(True),
                    Product.current_stock >= quantity
                )
                .values(
                    current_stock=Product.current_stock - quantity
                )
            )

            if result.rowcount != 1:
                db.session.rollback()
                return error("Estoque insuficiente", 409)

        else:
            result = db.session.execute(
                update(Product)
                .where(
                    Product.id == item.id,
                    Product.store_id == user.store_id,
                    Product.active.is_(True)
                )
                .values(
                    current_stock=Product.current_stock + quantity
                )
            )

            if result.rowcount != 1:
                db.session.rollback()
                return error("Produto indisponivel", 409)

        db.session.refresh(item)

        movement = StockMovement(
            product=item,
            user=user,
            type=kind,
            reason=reason,
            quantity=quantity,
            unit_cost=item.cost_price,
            note=note
        )

        db.session.add(movement)
        db.session.commit()

        return jsonify({
            "movement": serialize_movement(movement),
            "current_stock": str(item.current_stock),
            "is_low_stock": item.is_low_stock
        }), 201

    except ValueError as exc:
        db.session.rollback()
        return error(str(exc))


# ==========================================
# FILTROS DO HISTORICO
# ==========================================

def filtered_movements(user):
    query = (
        StockMovement.query
        .join(Product)
        .filter(Product.store_id == user.store_id)
    )

    if request.args.get("product_id"):
        try:
            product_id = int(request.args["product_id"])
        except ValueError:
            raise ValueError("product_id invalido")

        query = query.filter(
            StockMovement.product_id == product_id
        )

    if request.args.get("type"):
        movement_type = request.args["type"]

        if movement_type not in ("entrada", "saida"):
            raise ValueError("Tipo de movimentacao invalido")

        query = query.filter(
            StockMovement.type == movement_type
        )

    if request.args.get("start"):
        try:
            start = datetime.strptime(
                request.args["start"], "%Y-%m-%d"
            )
        except ValueError:
            raise ValueError("Data inicial invalida")

        query = query.filter(
            StockMovement.created_at >= start
        )

    if request.args.get("end"):
        try:
            end = datetime.strptime(
                request.args["end"], "%Y-%m-%d"
            )
        except ValueError:
            raise ValueError("Data final invalida")

        query = query.filter(
            StockMovement.created_at < end + timedelta(days=1)
        )

    return query


# ==========================================
# CONSULTAR HISTORICO
# ==========================================

@bp.get("/movements")
@authorized()
def list_movements(user):
    try:
        page = request.args.get(
            "page", default=1, type=int
        )
        limit = request.args.get(
            "limit", default=30, type=int
        )

        if page < 1 or limit < 1 or limit > 100:
            return error("Paginacao invalida")

        query = filtered_movements(user)

        result = (
            query.order_by(StockMovement.id.desc())
            .paginate(
                page=page,
                per_page=limit,
                error_out=False
            )
        )

        return jsonify({
            "items": [
                serialize_movement(x)
                for x in result.items
            ],
            "total": result.total,
            "page": page,
            "pages": result.pages
        })

    except ValueError as exc:
        return error(str(exc))


# ==========================================
# ALERTAS DE ESTOQUE MINIMO
# ==========================================

@bp.get("/alerts")
@authorized()
def alerts(user):
    items = (
        Product.query
        .filter_by(
            store_id=user.store_id,
            active=True
        )
        .filter(
            Product.current_stock <= Product.min_stock
        )
        .order_by(Product.current_stock)
        .all()
    )

    return jsonify({
        "count": len(items),
        "out_of_stock": sum(
            x.current_stock == 0 for x in items
        ),
        "items": [
            serialize_product(x) for x in items
        ]
    })


# ==========================================
# DASHBOARD DO ESTOQUE
# ==========================================

@bp.get("/dashboard")
@authorized(admin=True)
def dashboard(user):
    products = Product.query.filter_by(
        store_id=user.store_id,
        active=True
    ).all()

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)

    sold = (
        db.session.query(
            StockMovement.product_id,
            func.sum(StockMovement.quantity).label(
                "quantity"
            )
        )
        .join(Product)
        .filter(
            Product.store_id == user.store_id,
            StockMovement.type == "saida",
            StockMovement.reason == "venda",
            StockMovement.created_at >= month_start
        )
        .group_by(StockMovement.product_id)
        .order_by(
            func.sum(StockMovement.quantity).desc()
        )
        .limit(5)
        .all()
    )

    names = {
        product.id: product.name
        for product in products
    }

    missing_ids = [
        row.product_id for row in sold
        if row.product_id not in names
    ]

    if missing_ids:
        extra = Product.query.filter(
            Product.id.in_(missing_ids),
            Product.store_id == user.store_id
        ).all()

        names.update({
            product.id: product.name
            for product in extra
        })

    stock_value = sum(
        (p.stock_value for p in products),
        Decimal("0")
    )

    return jsonify({
        "total_products": len(products),
        "stock_value": str(stock_value),
        "low_stock_count": sum(
            p.is_low_stock for p in products
        ),
        "out_of_stock_count": sum(
            p.current_stock == 0 for p in products
        ),
        "top_selling_this_month": [
            {
                "product_id": row.product_id,
                "name": names.get(
                    row.product_id, "Produto"
                ),
                "quantity": str(row.quantity)
            }
            for row in sold
        ]
    })


# ==========================================
# CONTAGEM FISICA DO ESTOQUE
# ==========================================

@bp.post("/inventory-counts")
@authorized(admin=True)
def create_inventory_count(user):
    try:
        data = body()

        product_id = integer_field(
            data, "product_id", required=True
        )

        counted = decimal_field(
            data, "counted_quantity"
        )

        product = (
            Product.query
            .filter_by(
                id=product_id,
                store_id=user.store_id,
                active=True
            )
            .with_for_update()
            .first()
        )

        if product is None:
            return error("Produto nao encontrado", 404)

        previous = product.current_stock
        difference = counted - previous

        count = InventoryCount(
            product=product,
            user=user,
            system_quantity=previous,
            counted_quantity=counted
        )

        db.session.add(count)

        if difference:
            movement = StockMovement(
                product=product,
                user=user,
                type=(
                    "entrada"
                    if difference > 0
                    else "saida"
                ),
                reason="ajuste",
                quantity=abs(difference),
                unit_cost=product.cost_price,
                note="Ajuste por contagem fisica"
            )

            db.session.add(movement)
            product.current_stock = counted

        db.session.commit()

        return jsonify({
            "id": count.id,
            "product_id": product.id,
            "system_quantity": str(previous),
            "counted_quantity": str(counted),
            "difference": str(difference)
        }), 201

    except ValueError as exc:
        db.session.rollback()
        return error(str(exc))


# ==========================================
# CONSULTAR CONTAGENS FISICAS
# ==========================================

@bp.get("/inventory-counts")
@authorized(admin=True)
def list_counts(user):
    items = (
        InventoryCount.query
        .join(Product)
        .filter(Product.store_id == user.store_id)
        .order_by(InventoryCount.id.desc())
        .limit(100)
        .all()
    )

    return jsonify([
        {
            "id": count.id,
            "product_id": count.product_id,
            "user_id": count.user_id,
            "system_quantity": str(
                count.system_quantity
            ),
            "counted_quantity": str(
                count.counted_quantity
            ),
            "difference": str(count.difference),
            "created_at": as_date(count.created_at)
        }
        for count in items
    ])
