import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Category, Product, Stable, User


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
def haras(db):
    stable = Stable(name="Haras Teste")
    user = User(stable=stable, name="Admin", email="admin@teste.com", role="admin")
    user.set_password("123")
    category = Category(stable=stable, name="Ração")
    product = Product(stable=stable, category=category, name="Ração", code="1",
                      unit="kg", cost_price=10, min_stock=5)
    db.session.add_all([stable, user, category, product])
    db.session.commit()
    return {"stable": stable, "user": user, "category": category, "product": product}
