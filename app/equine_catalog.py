"""Cadastro não destrutivo de produtos em uma loja existente."""
import click
from app.extensions import db
from app.models import Store, Category, Product, ReplenishmentPolicy

CATALOG = [
    ('EQ001', 'Vermifugo equino', 'Produtos veterinarios', 'un', 10, 5, 2),
    ('EQ002', 'Racao equina', 'Alimentacao', 'kg', 140, 5, 2),
    ('EQ003', 'Feno', 'Alimentacao', 'kg', 70, 3, 2),
    ('EQ004', 'Sal mineral para equinos', 'Alimentacao', 'kg', 7, 5, 2),
    ('EQ005', 'Shampoo para equinos', 'Higiene', 'un', 2, 4, 2),
    ('EQ006', 'Produto para controle de carrapatos', 'Produtos veterinarios', 'un', 2, 5, 2),
]


@click.command('cadastrar-equinos')
@click.option('--store-id', type=int, required=True, help='ID da loja existente.')
def cadastrar_equinos(store_id):
    """Cadastra itens faltantes, com saldo zero; preserva itens e politicas existentes."""
    if db.session.get(Store, store_id) is None:
        raise click.ClickException('Loja nao encontrada. Nenhum dado foi alterado.')
    created = 0
    try:
        for code, name, category_name, unit, weekly, lead, safety in CATALOG:
            by_code = Product.query.filter_by(store_id=store_id, code=code).first()
            by_name = Product.query.filter_by(store_id=store_id, name=name).all()
            if (by_code and by_code.name != name) or len(by_name) > 1 or (by_code and by_name and by_name[0].id != by_code.id):
                raise ValueError(f'Conflito de nome/codigo: {name}. Cadastro cancelado.')
            product = by_code or (by_name[0] if by_name else None)
            if product and (product.unit != unit or not product.active):
                raise ValueError(f'Produto inativo ou unidade diferente: {name}. Cadastro cancelado.')
            if product is None:
                category = Category.query.filter_by(store_id=store_id, name=category_name).first()
                if category is None:
                    category = Category(store_id=store_id, name=category_name)
                    db.session.add(category)
                    db.session.flush()
                product = Product(store_id=store_id, category_id=category.id, name=name, code=code, unit=unit, current_stock=0)
                db.session.add(product)
                db.session.flush()
                created += 1
            if db.session.get(ReplenishmentPolicy, product.id) is None:
                db.session.add(ReplenishmentPolicy(product_id=product.id, weekly_consumption=weekly, lead_days=lead, safety_days=safety))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException(str(exc)) from exc
    click.echo(f'{created} produtos criados. Saldos e politicas existentes preservados. Novos produtos iniciam zerados; registre a entrada real via API.')
