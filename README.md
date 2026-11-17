# EstoqueFácil Equihealth

Controle de estoque dos insumos de um haras que usa o alimentador automático **Equihealth**: ração, volumoso (feno), suplementos e vitaminas. Trabalho de Programação Web Avançada II (UVV).

- Entradas: `compra`, `doacao`, `ajuste` (com lote e validade opcionais)
- Saídas: `abastecimento_alimentador`, `trato_manual`, `avaria`, `vencimento`, `furto`, `ajuste`
- Alerta de estoque mínimo, capital imobilizado e **dias de cobertura** (saldo ÷ consumo diário)
- Inventário (contagem física x sistema)

Monorepo com duas partes separadas:

| Pasta | O que é |
|---|---|
| `backend/` | API REST em Flask + SQLAlchemy (SQLite em desenvolvimento) |
| `front-end/` | Interface em Vue 3 (ainda não iniciado) |

## Configuração

O `.env` (SECRET_KEY e DATABASE_URL) fica na raiz do repositório e não vai pro Git. Crie a partir do modelo:

```bash
copy .env.example .env
```

O Flask o encontra subindo as pastas pais a partir de `backend/`.

## Backend

Todos os comandos abaixo rodam de dentro de `backend/`.

### 1. Primeira vez (no terminal do VS Code, `Ctrl + '`)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev,test]"
```

Depois: `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha `backend\venv`.

### 2. Criar o banco

```bash
flask db upgrade                   # aplica as migrations já versionadas em migrations/
flask seed                         # dados de exemplo (APAGA e recria os dados do banco)
```

O banco SQLite fica em `backend/instance/dev.db` (abra com a extensão **SQLite Viewer**).

Usuários de exemplo:
- `admin@haras.com` / `admin123` (admin)
- `tratador@haras.com` / `trat123` (tratador)

### 3. Rodar a API e os testes

```bash
flask run
pytest -v
```

### 4. Quando alterar o `models.py`

Só depois de mudar o `models.py`, gere uma nova migration (não edite uma já aplicada):

```bash
flask db migrate -m "descreva a mudança"
flask db upgrade
```

### Atalhos com invoke

| Comando | Faz |
|---|---|
| `invoke install` | instala dependências |
| `invoke migrate --msg "texto"` | gera migração |
| `invoke upgrade` | aplica migrações |
| `invoke seed` | popula o banco |
| `invoke test` | roda os testes |

### Estrutura

```
estoquefacilapp/
├── .env                # SECRET_KEY e DATABASE_URL (não vai pro Git)
├── .env.example
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py     # create_app()
│   │   ├── extensions.py   # db e migrate
│   │   ├── models.py       # tabelas do banco
│   │   └── seed.py         # comando "flask seed"
│   ├── migrations/         # migrations do Flask-Migrate (versionadas)
│   ├── instance/           # banco SQLite local, dev.db (não vai pro Git)
│   ├── tests/
│   │   ├── conftest.py     # fixtures do pytest
│   │   └── test_models.py  # testes do banco
│   ├── config.py           # Dev / Testing / Production
│   ├── .flaskenv           # FLASK_APP=app
│   ├── pyproject.toml
│   └── tasks.py
└── front-end/
```

## Front-end

Ainda não iniciado.
