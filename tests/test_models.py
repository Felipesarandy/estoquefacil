from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Category, InventoryCount, Product, StockMovement, User
from app.seed import registrar_movimentacao


def test_senha_com_hash(loja):
    user = loja["user"]
    assert user.password_hash != "123"
    assert user.check_password("123")
    assert not user.check_password("errada")


def test_entrada_aumenta_saldo(db, loja):
    p = loja["product"]
    registrar_movimentacao(p, loja["user"], "entrada", "compra", 10)
    db.session.commit()
    assert p.current_stock == 10
    assert len(p.movements) == 1


def test_saida_maior_que_saldo_e_bloqueada(loja):
    with pytest.raises(ValueError):
        registrar_movimentacao(loja["product"], loja["user"], "saida", "venda", 1)


def test_alerta_estoque_minimo(db, loja):
    p = loja["product"]
    registrar_movimentacao(p, loja["user"], "entrada", "compra", 5)
    assert p.is_low_stock          # 5 <= 5
    registrar_movimentacao(p, loja["user"], "entrada", "compra", 1)
    assert not p.is_low_stock      # 6 > 5


def test_capital_imobilizado(db, loja):
    p = loja["product"]
    registrar_movimentacao(p, loja["user"], "entrada", "compra", 3)
    assert p.stock_value == Decimal("30")   # 3 x R$ 10


def test_diferenca_inventario(db, loja):
    c = InventoryCount(product=loja["product"], user=loja["user"],
                       system_quantity=10, counted_quantity=8)
    db.session.add(c)
    db.session.commit()
    assert c.difference == -2


def test_email_unico(db, loja):
    db.session.add(User(store=loja["store"], name="X", email="admin@teste.com", password_hash="h"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_categoria_unica_por_loja(db, loja):
    db.session.add(Category(store=loja["store"], name="Geral"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_codigo_unico_por_loja(db, loja):
    db.session.add(Product(store=loja["store"], category=loja["category"], name="Outro", code="1"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_quantidade_deve_ser_positiva(db, loja):
    db.session.add(StockMovement(product=loja["product"], user=loja["user"], type="entrada",
                                 reason="compra", quantity=0, unit_cost=1))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_saldo_nao_pode_ser_negativo(db, loja):
    loja["product"].current_stock = -1
    with pytest.raises(IntegrityError):
        db.session.commit()
