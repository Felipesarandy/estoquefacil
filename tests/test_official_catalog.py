from decimal import Decimal
from app.models import Product, ReplenishmentPolicy


def test_catalog_non_destructive(app, loja, db):
    runner = app.test_cli_runner()
    store_id = loja['store'].id
    old_id = loja['product'].id
    args = ['cadastrar-equinos', '--store-id', str(store_id)]
    assert runner.invoke(args=args).exit_code == 0
    assert Product.query.count() == 7
    assert ReplenishmentPolicy.query.count() == 6
    product = Product.query.filter_by(code='EQ001').one()
    assert product.current_stock == 0
    product.current_stock = Decimal(8)
    policy = db.session.get(ReplenishmentPolicy, product.id)
    policy.weekly_consumption = 4
    db.session.commit()
    assert runner.invoke(args=args).exit_code == 0
    assert Product.query.count() == 7
    assert db.session.get(Product, product.id).current_stock == 8
    assert db.session.get(ReplenishmentPolicy, product.id).weekly_consumption == 4
    assert db.session.get(Product, old_id).name == 'Produto'
    assert runner.invoke(args=['cadastrar-equinos', '--store-id', '99999']).exit_code != 0
