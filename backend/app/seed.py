"""Dados iniciais para desenvolvimento e testes.

Uso:  flask seed
"""
from datetime import date
from decimal import Decimal

import click

from app.extensions import db
from app.models import (
    Category, InventoryCount, Product, Stable, StockMovement, Supplier, User,
)


def registrar_movimentacao(produto, usuario, tipo, motivo, quantidade, obs=None,
                           lote=None, validade=None):
    """Cria a movimentação e atualiza o saldo na mesma operação."""
    quantidade = Decimal(str(quantidade))
    if tipo == "saida" and quantidade > produto.current_stock:
        raise ValueError(f"Saldo insuficiente de {produto.name}")

    mov = StockMovement(
        product=produto, user=usuario, type=tipo, reason=motivo,
        quantity=quantidade, unit_cost=produto.cost_price, note=obs,
        batch=lote, expiration_date=validade,
    )
    if tipo == "entrada":
        produto.current_stock += quantidade
    else:
        produto.current_stock -= quantidade
    db.session.add(mov)
    return mov


@click.command("seed")
def seed_command():
    """Apaga os dados e popula o banco com um haras de exemplo."""
    # limpa as tabelas (das "filhas" para as "mães"), mantendo a estrutura das migrações
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())

    haras = Stable(name="Haras Exemplo", city="Vila Velha")

    admin = User(stable=haras, name="Felipe Admin", email="admin@haras.com", role="admin")
    admin.set_password("admin123")
    tratador = User(stable=haras, name="João Tratador", email="tratador@haras.com", role="tratador")
    tratador.set_password("trat123")

    racao = Category(stable=haras, name="Ração")
    volumoso = Category(stable=haras, name="Volumoso")
    suplementos = Category(stable=haras, name="Suplementos")
    vitaminas = Category(stable=haras, name="Vitaminas")

    nutriequi = Supplier(stable=haras, name="Nutriequi Rações", phone="(27) 3333-0001",
                         email="vendas@nutriequi.com")
    agro = Supplier(stable=haras, name="Agropecuária Capixaba", phone="(27) 3333-0002")

    produtos = [
        Product(stable=haras, category=racao, supplier=nutriequi, name="Ração peletizada 14% PB",
                code="EQ001", unit="kg", cost_price=Decimal("3.20"),
                min_stock=Decimal("100"), max_stock=Decimal("600"), daily_consumption=Decimal("24")),
        Product(stable=haras, category=racao, supplier=nutriequi, name="Ração extrusada performance",
                code="EQ002", unit="kg", cost_price=Decimal("5.80"),
                min_stock=Decimal("50"), daily_consumption=Decimal("8")),
        Product(stable=haras, category=volumoso, supplier=agro, name="Feno de tifton (fardo)",
                code="EQ100", unit="un", cost_price=Decimal("35.00"),
                min_stock=Decimal("10"), daily_consumption=Decimal("2")),
        Product(stable=haras, category=suplementos, supplier=agro, name="Sal mineral",
                code="EQ200", unit="kg", cost_price=Decimal("6.00"),
                min_stock=Decimal("10"), daily_consumption=Decimal("0.4")),
        Product(stable=haras, category=suplementos, supplier=agro, name="Óleo de soja",
                code="EQ201", unit="l", cost_price=Decimal("9.00"),
                min_stock=Decimal("5"), daily_consumption=Decimal("0.5")),
        Product(stable=haras, category=vitaminas, supplier=nutriequi, name="Suplemento vitamínico em pó",
                code="EQ300", unit="kg", cost_price=Decimal("48.00"),
                min_stock=Decimal("2"), daily_consumption=Decimal("0.2")),
    ]
    db.session.add_all([haras, admin, tratador, racao, volumoso, suplementos, vitaminas,
                        nutriequi, agro, *produtos])
    db.session.flush()

    peletizada, extrusada, feno, sal, oleo, vitamina = produtos

    # Entradas (compras), com lote e validade
    registrar_movimentacao(peletizada, admin, "entrada", "compra", 500, "20 sacos de 25 kg",
                           lote="L2611A", validade=date(2027, 3, 1))
    registrar_movimentacao(extrusada, admin, "entrada", "compra", 120,
                           lote="L2611B", validade=date(2027, 2, 15))
    registrar_movimentacao(feno, admin, "entrada", "compra", 40)
    registrar_movimentacao(sal, admin, "entrada", "compra", 25, lote="S1029", validade=date(2027, 10, 1))
    registrar_movimentacao(oleo, admin, "entrada", "compra", 20)
    registrar_movimentacao(vitamina, admin, "entrada", "compra", 5, lote="V0915", validade=date(2027, 1, 30))

    # Saídas (alimentador, trato manual e quebra)
    registrar_movimentacao(peletizada, tratador, "saida", "abastecimento_alimentador", 420)  # abaixo do mínimo
    registrar_movimentacao(extrusada, tratador, "saida", "trato_manual", 40)
    registrar_movimentacao(feno, tratador, "saida", "trato_manual", 32)          # abaixo do mínimo
    registrar_movimentacao(sal, tratador, "saida", "trato_manual", 12)
    registrar_movimentacao(oleo, tratador, "saida", "trato_manual", 10)
    registrar_movimentacao(oleo, tratador, "saida", "avaria", 2, "Galão furado")
    registrar_movimentacao(vitamina, tratador, "saida", "trato_manual", 3)       # fica no mínimo

    # Auditoria: contagem física encontrou 1 kg de sal mineral a menos
    contagem = InventoryCount(product=sal, user=admin,
                              system_quantity=sal.current_stock, counted_quantity=Decimal("12"))
    db.session.add(contagem)
    registrar_movimentacao(sal, admin, "saida", "ajuste", 1, "Ajuste após inventário")

    db.session.commit()

    em_alerta = [p.name for p in produtos if p.is_low_stock]
    click.echo("Banco populado!")
    click.echo("  admin@haras.com    / admin123  (admin)")
    click.echo("  tratador@haras.com / trat123   (tratador)")
    click.echo(f"  Insumos em alerta: {', '.join(em_alerta)}")
