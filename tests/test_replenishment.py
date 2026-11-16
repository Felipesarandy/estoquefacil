from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend_app import create_app
from app.models import Product, StockMovement
from app.routes.replenishment import plan
from test_api import criar_admin


@pytest.fixture
def app():
    from app.extensions import db
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def setup_product(client):
    auth = criar_admin(client)
    category = client.post('/api/categories', headers=auth, json={'name': 'Equinos'}).json['id']
    product = client.post('/api/products', headers=auth, json={'name': 'Vermifugo', 'category_id': category}).json['id']
    client.post('/api/movements', headers=auth, json={'product_id': product, 'type': 'entrada', 'reason': 'compra', 'quantity': 10})
    response = client.put(f'/api/products/{product}/replenishment-policy', headers=auth, json={'weekly_consumption': 10, 'lead_days': 5, 'safety_days': 2, 'order_quantity': 10})
    assert response.status_code == 200
    return auth, product, response.json


def test_reorder_and_unified_alert(client):
    auth, product, result = setup_product(client)
    assert Decimal(result['safety_stock']) == 3
    assert Decimal(result['reorder_point']) == 11
    assert result['reorder_needed']
    assert 'pending_orders' not in result
    assert client.get(f'/api/products/{product}', headers=auth).json['is_low_stock']
    assert client.get('/api/alerts', headers=auth).json['count'] == 1
    assert client.post('/api/purchase-orders', headers=auth, json={}).status_code == 404
    assert client.get('/api/purchase-orders', headers=auth).status_code == 404
    client.post('/api/movements', headers=auth, json={'product_id': product, 'type': 'entrada', 'reason': 'compra', 'quantity': 10})
    assert not client.get('/api/replenishment', headers=auth).json[0]['reorder_needed']
    assert not client.get(f'/api/products/{product}', headers=auth).json['is_low_stock']
    assert client.get('/api/alerts', headers=auth).json['count'] == 0


def test_risk_and_isolation(client):
    auth, product, _ = setup_product(client)
    client.post('/api/movements', headers=auth, json={'product_id': product, 'type': 'saida', 'reason': 'uso_interno', 'quantity': 4})
    assert client.get('/api/replenishment', headers=auth).json[0]['stockout_risk']
    other = criar_admin(client, 'other@loja.com', 'Outra')
    assert client.get('/api/replenishment', headers=other).json == []


@pytest.mark.parametrize('field,value', [('weekly_consumption', 0), ('weekly_consumption', 'NaN'), ('lead_days', -1), ('lead_days', True), ('safety_days', 1.5)])
def test_invalid_policy(client, field, value):
    auth, product, _ = setup_product(client)
    data = dict(weekly_consumption=10, lead_days=5, safety_days=2, order_quantity=10)
    data[field] = value
    assert client.put(f'/api/products/{product}/replenishment-policy', headers=auth, json=data).status_code == 400
