
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# Motivos aceitos em cada tipo de movimentação (validar na API)
MOTIVOS_ENTRADA = ["compra", "doacao", "ajuste"]
MOTIVOS_SAIDA = [
    "abastecimento_alimentador",  # reposição do reservatório do alimentador Equihealth
    "trato_manual",               # ração/suplemento dado à mão pelo tratador
    "avaria",                     # saco rasgado, umidade, mofo, roedores
    "vencimento",
    "furto",
    "ajuste",
]
MOTIVOS_QUEBRA = ["avaria", "vencimento", "furto"]  # perdas (quebra de estoque)

UNIDADES = ["kg", "g", "sc", "l", "ml", "un"]  # sc = saco | un = fardo, bisnaga, frasco...


class Stable(db.Model):
    """Haras / propriedade que usa o Equihealth."""
    __tablename__ = "stables"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    users = db.relationship("User", backref="stable")
    categories = db.relationship("Category", backref="stable")
    suppliers = db.relationship("Supplier", backref="stable")
    products = db.relationship("Product", backref="stable")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="tratador")  # admin | tratador
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    movements = db.relationship("StockMovement", backref="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    """Ex.: Ração, Volumoso, Suplementos, Vitaminas."""
    __tablename__ = "categories"
    __table_args__ = (db.UniqueConstraint("stable_id", "name"),)

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)

    products = db.relationship("Product", backref="category")


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))

    products = db.relationship("Product", backref="supplier")


class Product(db.Model):
    """Insumo do haras: ração, feno, suplemento, vitamina..."""
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("stable_id", "code"),
        db.CheckConstraint("current_stock >= 0", name="ck_products_saldo_positivo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))  # opcional
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50))  # código interno / de barras (opcional)
    unit = db.Column(db.String(10), nullable=False, default="kg")  # ver UNIDADES
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # custo por unidade
    min_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)  # estoque de segurança
    max_stock = db.Column(db.Numeric(10, 3))  # opcional: evita comprar demais (vencimento)
    current_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    daily_consumption = db.Column(db.Numeric(10, 3))  # consumo médio por dia (opcional)
    active = db.Column(db.Boolean, default=True)

    movements = db.relationship("StockMovement", backref="product")
    inventory_counts = db.relationship("InventoryCount", backref="product")

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock

    @property
    def stock_value(self):
        """Capital imobilizado no insumo (saldo x custo)."""
        return self.current_stock * self.cost_price

    @property
    def days_left(self):
        """Quantos dias o saldo atual dura no consumo médio (None se não informado)."""
        if not self.daily_consumption:
            return None
        return self.current_stock / self.daily_consumption


class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_movements_quantidade_positiva"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(10), nullable=False)    # entrada | saida
    reason = db.Column(db.String(30), nullable=False)  # ver MOTIVOS_ENTRADA / MOTIVOS_SAIDA
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)  # custo unitário no momento
    batch = db.Column(db.String(50))         # lote (entradas)
    expiration_date = db.Column(db.Date)     # validade do lote (entradas)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


class InventoryCount(db.Model):
    """Auditoria de estoque: contagem física de um insumo."""
    __tablename__ = "inventory_counts"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    system_quantity = db.Column(db.Numeric(10, 3), nullable=False)   # saldo no sistema
    counted_quantity = db.Column(db.Numeric(10, 3), nullable=False)  # quantidade contada
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User")

    @property
    def difference(self):
        """Negativo = faltou insumo (quebra); positivo = sobrou."""
        return self.counted_quantity - self.system_quantity
