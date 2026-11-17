# EstoqueFácil Equihealth — Backend (parte do banco de dados)

Controle de estoque dos insumos de um haras que usa o alimentador automático **Equihealth**: ração, volumoso (feno), suplementos e vitaminas.

- Entradas: `compra`, `doacao`, `ajuste` (com lote e validade opcionais)
- Saídas: `abastecimento_alimentador`, `trato_manual`, `avaria`, `vencimento`, `furto`, `ajuste`
- Alerta de estoque mínimo, capital imobilizado e **dias de cobertura** (saldo ÷ consumo diário)
- Inventário (contagem física x sistema)

## 1. Primeira vez (no terminal do VS Code, `Ctrl + '`)

Todos os comandos abaixo rodam de dentro da pasta `backend/`.

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev,test]"
```

Depois: `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha o `venv`.

## 2. Criar o banco

```bash
flask db init                      # só na primeira vez (cria a pasta migrations/)
flask db migrate -m "modelo inicial"
flask db upgrade
flask seed                         # dados de exemplo
```

O banco SQLite fica em `instance/dev.db` (abra com a extensão **SQLite Viewer**).

Usuários de exemplo:
- `admin@haras.com` / `admin123` (admin)
- `tratador@haras.com` / `trat123` (tratador)

## 3. Rodar os testes

```bash
pytest -v
```

## 4. Quando alterar o `models.py`

```bash
flask db migrate -m "descreva a mudança"
flask db upgrade
```

## Atalhos com invoke

| Comando | Faz |
|---|---|
| `invoke install` | instala dependências |
| `invoke migrate --msg "texto"` | gera migração |
| `invoke upgrade` | aplica migrações |
| `invoke seed` | popula o banco |
| `invoke test` | roda os testes |

## Estrutura

```
backend/
├── app/
│   ├── __init__.py     # create_app()
│   ├── extensions.py   # db e migrate
│   ├── models.py       # tabelas do banco
│   └── seed.py         # comando "flask seed"
├── tests/
│   ├── conftest.py     # fixtures do pytest
│   └── test_models.py  # testes do banco
├── config.py           # Dev / Testing / Production
├── .flaskenv           # FLASK_APP=app
├── pyproject.toml
└── tasks.py
```

O `.env` (SECRET_KEY e DATABASE_URL, não vai pro Git) fica na raiz do repositório (`../.env`). O Flask o encontra subindo pelas pastas pais. Modelo em `../.env.example`.
