
import pytest

from backend_app import create_app
from app.extensions import db


# Banco temporario apenas para os testes
@pytest.fixture
def app():
    aplicativo = create_app("testing")

    with aplicativo.app_context():
        db.create_all()
        yield aplicativo
        db.session.remove()
        db.drop_all()


# Cria uma loja e realiza login como administrador
def criar_admin(client, email="admin@loja.com", loja="Loja Teste"):
    resposta = client.post("/api/auth/register", json={
        "store_name": loja,
        "name": "Administrador",
        "email": email,
        "password": "senha12345"
    })

    assert resposta.status_code == 201, resposta.get_json()

    login = client.post("/api/auth/login", json={
        "email": email,
        "password": "senha12345"
    })

    assert login.status_code == 200
    token = login.get_json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# TESTE 1: API e protecao dos produtos
def test_autenticacao(client):
    resposta = client.get("/api/health")
    assert resposta.status_code == 200

    resposta = client.get("/api/products")
    assert resposta.status_code == 401


# TESTE 2: Cadastro de loja e login
def test_cadastro_login(client):
    headers = criar_admin(client)

    resposta = client.get("/api/auth/me", headers=headers)

    assert resposta.status_code == 200
    assert resposta.get_json()["role"] == "admin"


# TESTE 3: Permissoes do funcionario
def test_permissoes(client):
    admin = criar_admin(client)

    resposta = client.post("/api/users", headers=admin, json={
        "name": "Funcionario",
        "email": "funcionario@loja.com",
        "password": "senha12345"
    })

    assert resposta.status_code == 201

    login = client.post("/api/auth/login", json={
        "email": "funcionario@loja.com",
        "password": "senha12345"
    })

    assert login.status_code == 200

    funcionario = {
        "Authorization": "Bearer " + login.get_json()["access_token"]
    }

    # Funcionario nao pode cadastrar categorias
    resposta = client.post(
        "/api/categories",
        headers=funcionario,
        json={"name": "Materiais"}
    )

    assert resposta.status_code == 403

    # Mas pode consultar produtos
    resposta = client.get("/api/products", headers=funcionario)
    assert resposta.status_code == 200


# TESTE 4: Entrada, saida e estoque insuficiente
def test_movimentacao_estoque(client):
    headers = criar_admin(client)

    categoria = client.post(
        "/api/categories",
        headers=headers,
        json={"name": "Papelaria"}
    )
    assert categoria.status_code == 201

    produto = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "Caneta",
            "category_id": categoria.get_json()["id"],
            "cost_price": "2.00",
            "min_stock": "8"
        }
    )
    assert produto.status_code == 201

    produto_id = produto.get_json()["id"]

    def movimentar(tipo, quantidade, motivo):
        return client.post("/api/movements", headers=headers, json={
            "product_id": produto_id,
            "type": tipo,
            "quantity": quantidade,
            "reason": motivo
        })

    # Nao permite saida sem estoque
    assert movimentar("saida", 1, "venda").status_code == 409

    # Entrada de 10 unidades
    assert movimentar("entrada", 10, "compra").status_code == 201

    # Saida de 3 unidades
    assert movimentar("saida", 3, "venda").status_code == 201

    # Saldo esperado: 7 unidades
    resposta = client.get(
        f"/api/products/{produto_id}",
        headers=headers
    )

    assert resposta.status_code == 200
    assert float(resposta.get_json()["current_stock"]) == 7

    # Com minimo de 8, produto deve gerar alerta
    alertas = client.get("/api/alerts", headers=headers)
    assert alertas.status_code == 200
    assert alertas.get_json()["count"] == 1


# TESTE 5: Separacao de dados entre lojas
def test_isolamento_entre_lojas(client):
    loja_a = criar_admin(client)

    categoria = client.post(
        "/api/categories",
        headers=loja_a,
        json={"name": "Produtos A"}
    )
    assert categoria.status_code == 201

    produto = client.post(
        "/api/products",
        headers=loja_a,
        json={
            "name": "Produto exclusivo",
            "category_id": categoria.get_json()["id"]
        }
    )
    assert produto.status_code == 201

    produto_id = produto.get_json()["id"]

    loja_b = criar_admin(
        client,
        email="admin@lojab.com",
        loja="Loja B"
    )

    # Loja B nao pode acessar produto da Loja A
    resposta = client.get(
        f"/api/products/{produto_id}",
        headers=loja_b
    )

    assert resposta.status_code == 404
