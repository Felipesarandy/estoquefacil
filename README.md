# EstoqueFácil — Backend (parte do banco de dados)

## 1. Primeira vez (no terminal do VS Code, `Ctrl + '`)

```bash
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
- `admin@loja.com` / `admin123` (admin)
- `func@loja.com` / `func123` (funcionário)

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
estoquefacil-backend/
├── app/
│   ├── __init__.py     # create_app()
│   ├── extensions.py   # db e migrate
│   ├── models.py       # tabelas do banco
│   └── seed.py         # comando "flask seed"
├── tests/
│   ├── conftest.py     # fixtures do pytest
│   └── test_models.py  # testes do banco
├── config.py           # Dev / Testing / Production
├── .env                # SECRET_KEY e DATABASE_URL (não vai pro Git)
├── .flaskenv           # FLASK_APP=app
├── pyproject.toml
└── tasks.py
```
