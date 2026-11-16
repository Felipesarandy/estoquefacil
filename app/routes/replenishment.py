"""Controle de reposição e previsão de ruptura; sem pedidos de compra."""
from decimal import Decimal, ROUND_CEILING

from flask import Blueprint, jsonify

from app.extensions import db
from app.models import Product, ReplenishmentPolicy
from app.routes.common import authorized, body, decimal_field, error, scoped

bp = Blueprint('replenishment', __name__, url_prefix='/api')


def ceil_quantity(value, unit):
    return value.quantize(Decimal('1') if unit in ('un', 'cx') else Decimal('.001'), rounding=ROUND_CEILING)


def plan(product, policy):
    daily = policy.weekly_consumption / Decimal(7)
    safety = ceil_quantity(daily * policy.safety_days, product.unit)
    point = ceil_quantity(daily * policy.lead_days + safety, product.unit)
    return dict(product_id=product.id, name=product.name, unit=product.unit,
                current_stock=str(product.current_stock), weekly_consumption=str(policy.weekly_consumption),
                daily_consumption=str(daily.quantize(Decimal('.000001'))),
                lead_days=policy.lead_days, safety_days=policy.safety_days,
                safety_stock=str(safety), reorder_point=str(point),
                days_of_stock=str((product.current_stock / daily).quantize(Decimal('.01'))),
                reorder_needed=product.current_stock <= point,
                stockout_risk=product.current_stock < daily * policy.lead_days)


@bp.put('/products/<int:product_id>/replenishment-policy')
@authorized(admin=True)
def set_policy(user, product_id):
    product = scoped(Product, product_id, user)
    if product is None or not product.active:
        return error('Produto ativo nao encontrado', 404)
    try:
        data = body()
        weekly = decimal_field(data, 'weekly_consumption', positive=True)
        days = {}
        for key in ('lead_days', 'safety_days'):
            value = data.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3650:
                raise ValueError(f'{key} deve ser inteiro entre 0 e 3650')
            days[key] = value
        policy = db.session.get(ReplenishmentPolicy, product.id)
        if policy is None:
            policy = ReplenishmentPolicy(product_id=product.id)
            db.session.add(policy)
        policy.weekly_consumption = weekly
        policy.lead_days = days['lead_days']
        policy.safety_days = days['safety_days']
        db.session.commit()
        return jsonify(plan(product, policy))
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc))


@bp.get('/replenishment')
@authorized()
def replenishment(user):
    rows = db.session.query(Product, ReplenishmentPolicy).join(ReplenishmentPolicy, Product.id == ReplenishmentPolicy.product_id).filter(Product.store_id == user.store_id, Product.active.is_(True)).order_by(Product.id).all()
    return jsonify([plan(product, policy) for product, policy in rows])
