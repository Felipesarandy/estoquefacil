from decimal import Decimal
from app.models import Product, ReplenishmentPolicy
from app.routes.replenishment import plan


def test_equine_catalog_policies(app, loja):
    runner = app.test_cli_runner()
    assert runner.invoke(args=['cadastrar-equinos', '--store-id', str(loja['store'].id)]).exit_code == 0
    expected = {'EQ001': Decimal(11), 'Racao equina': Decimal(140), 'Feno': Decimal(50), 'Sal mineral para equinos': Decimal(7), 'Shampoo para equinos': Decimal(3), 'Produto para controle de carrapatos': Decimal(3)}
    assert Product.query.count() == 7
    assert ReplenishmentPolicy.query.count() == 6
    for product in Product.query.filter(Product.code.like("EQ%")):
        assert product.current_stock == 0
        result = plan(product, ReplenishmentPolicy.query.filter_by(product_id=product.id).one())
        assert Decimal(result['reorder_point']) == expected.get(product.code, expected.get(product.name))
    balances = [(p.id, p.current_stock) for p in Product.query.all()]
    assert runner.invoke(args=['cadastrar-equinos', '--store-id', str(loja['store'].id)]).exit_code == 0
    assert balances == [(p.id, p.current_stock) for p in Product.query.all()]


def test_demo_commands_removed(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=['seed']).exit_code != 0
    assert runner.invoke(args=['seed-equinos']).exit_code != 0
