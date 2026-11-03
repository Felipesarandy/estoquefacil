"""Dados iniciais para desenvolvimento e testes.

Uso:  flask seed
"""
from decimal import Decimal

import click

from app.extensions import db
from app.models import (
    Category, InventoryCount, Product, StockMovement, Store, Supplier, User,
)


def registrar_movimentacao(produto, usuario, tipo, motivo, quantidade, obs=None):
    """Cria a movimentação e atualiza o saldo na mesma operação."""
    quantidade = Decimal(str(quantidade))
    if tipo == "saida" and quantidade > produto.current_stock:
        raise ValueError(f"Saldo insuficiente de {produto.name}")

    mov = StockMovement(
        product=produto, user=usuario, type=tipo, reason=motivo,
        quantity=quantidade, unit_cost=produto.cost_price, note=obs,
    )
    if tipo == "entrada":
        produto.current_stock += quantidade
    else:
        produto.current_stock -= quantidade
    db.session.add(mov)
    return mov


@click.command("seed")
def seed_command():
    """Apaga os dados e popula o banco com uma loja de exemplo."""
    # limpa as tabelas (das "filhas" para as "mães"), mantendo a estrutura das migrações
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())

    loja = Store(name="Papelaria Exemplo", business_type="Papelaria")

    admin = User(store=loja, name="Felipe Admin", email="admin@loja.com", role="admin")
    admin.set_password("admin123")
    func = User(store=loja, name="Ana Funcionária", email="func@loja.com", role="funcionario")
    func.set_password("func123")

    cadernos = Category(store=loja, name="Cadernos")
    escrita = Category(store=loja, name="Escrita")
    papel = Category(store=loja, name="Papel")

    tilibra = Supplier(store=loja, name="Tilibra", phone="(27) 3333-0001", email="vendas@tilibra.com")
    bic = Supplier(store=loja, name="BIC", phone="(27) 3333-0002")

    produtos = [
        Product(store=loja, category=cadernos, supplier=tilibra, name="Caderno 10 matérias",
                code="789100", unit="un", cost_price=Decimal("18.00"), sale_price=Decimal("32.90"),
                min_stock=Decimal("5"), max_stock=Decimal("40")),
        Product(store=loja, category=cadernos, supplier=tilibra, name="Caderno brochura 96 fls",
                code="789101", unit="un", cost_price=Decimal("6.50"), sale_price=Decimal("12.90"),
                min_stock=Decimal("10")),
        Product(store=loja, category=escrita, supplier=bic, name="Caneta azul",
                code="789200", unit="un", cost_price=Decimal("1.20"), sale_price=Decimal("2.50"),
                min_stock=Decimal("30")),
        Product(store=loja, category=escrita, supplier=bic, name="Lápis HB",
                code="789201", unit="un", cost_price=Decimal("0.80"), sale_price=Decimal("1.80"),
                min_stock=Decimal("20")),
        Product(store=loja, category=papel, name="Papel A4 (resma)",
                code="789300", unit="cx", cost_price=Decimal("24.00"), sale_price=Decimal("34.90"),
                min_stock=Decimal("3")),
        Product(store=loja, category=papel, name="Papel kraft",
                unit="m", cost_price=Decimal("2.00"), sale_price=Decimal("4.50"),
                min_stock=Decimal("10")),
    ]
    db.session.add_all([loja, admin, func, cadernos, escrita, papel, tilibra, bic, *produtos])
    db.session.flush()

    caderno10, brochura, caneta, lapis, a4, kraft = produtos

    # Entradas (compras)
    registrar_movimentacao(caderno10, admin, "entrada", "compra", 20)
    registrar_movimentacao(brochura, admin, "entrada", "compra", 30)
    registrar_movimentacao(caneta, admin, "entrada", "compra", 100)
    registrar_movimentacao(lapis, admin, "entrada", "compra", 50)
    registrar_movimentacao(a4, admin, "entrada", "compra", 5)
    registrar_movimentacao(kraft, admin, "entrada", "compra", 25.5)

    # Saídas (vendas, uso interno e quebra)
    registrar_movimentacao(caderno10, func, "saida", "venda", 8)
    registrar_movimentacao(brochura, func, "saida", "venda", 22)   # fica abaixo do mínimo
    registrar_movimentacao(caneta, func, "saida", "venda", 75)     # fica abaixo do mínimo
    registrar_movimentacao(lapis, func, "saida", "venda", 12)
    registrar_movimentacao(a4, func, "saida", "uso_interno", 1)
    registrar_movimentacao(a4, func, "saida", "avaria", 1, "Caixa molhada")
    registrar_movimentacao(kraft, func, "saida", "venda", 25.5)    # zera o estoque

    # Auditoria: contagem física encontrou 2 lápis a menos
    contagem = InventoryCount(product=lapis, user=admin,
                              system_quantity=lapis.current_stock, counted_quantity=Decimal("36"))
    db.session.add(contagem)
    registrar_movimentacao(lapis, admin, "saida", "ajuste", 2, "Ajuste após inventário")

    db.session.commit()

    em_alerta = [p.name for p in produtos if p.is_low_stock]
    click.echo("Banco populado!")
    click.echo("  admin@loja.com / admin123  (admin)")
    click.echo("  func@loja.com  / func123   (funcionário)")
    click.echo(f"  Produtos em alerta: {', '.join(em_alerta)}")
