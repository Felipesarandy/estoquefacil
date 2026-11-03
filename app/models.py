
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# Motivos aceitos em cada tipo de movimentação (validar na API)
MOTIVOS_ENTRADA = ["compra", "devolucao_cliente", "ajuste"]
MOTIVOS_SAIDA = ["venda", "uso_interno", "avaria", "vencimento", "furto", "ajuste"]
MOTIVOS_QUEBRA = ["avaria", "vencimento", "furto"]  # perdas (quebra de estoque)


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    business_type = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    users = db.relationship("User", backref="store")
    categories = db.relationship("Category", backref="store")
    suppliers = db.relationship("Supplier", backref="store")
    products = db.relationship("Product", backref="store")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="funcionario")  # admin | funcionario
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    movements = db.relationship("StockMovement", backref="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (db.UniqueConstraint("store_id", "name"),)

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)

    products = db.relationship("Product", backref="category")


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))

    products = db.relationship("Product", backref="supplier")


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("store_id", "code"),
        db.CheckConstraint("current_stock >= 0", name="ck_products_saldo_positivo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))  # opcional
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50))  # SKU / código de barras (opcional)
    unit = db.Column(db.String(10), nullable=False, default="un")  # un | kg | l | m | cx
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    min_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)  # estoque de segurança
    max_stock = db.Column(db.Numeric(10, 3))  # opcional: evita capital imobilizado em excesso
    current_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    active = db.Column(db.Boolean, default=True)

    movements = db.relationship("StockMovement", backref="product")
    inventory_counts = db.relationship("InventoryCount", backref="product")

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock

    @property
    def stock_value(self):
        """Capital imobilizado no produto (saldo x custo)."""
        return self.current_stock * self.cost_price


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
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


class InventoryCount(db.Model):
    """Auditoria de estoque: contagem física de um produto."""
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
        """Negativo = faltou produto (quebra); positivo = sobrou."""
        return self.counted_quantity - self.system_quantity
