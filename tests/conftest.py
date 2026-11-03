import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Category, Product, Store, User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def loja(db):
    store = Store(name="Loja Teste")
    user = User(store=store, name="Admin", email="admin@teste.com", role="admin")
    user.set_password("123")
    category = Category(store=store, name="Geral")
    product = Product(store=store, category=category, name="Produto", code="1",
                      cost_price=10, min_stock=5)
    db.session.add_all([store, user, category, product])
    db.session.commit()
    return {"store": store, "user": user, "category": category, "product": product}
