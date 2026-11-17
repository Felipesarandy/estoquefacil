# EstoqueFácil Equihealth

Controle de estoque dos insumos de um haras que usa o alimentador automático **Equihealth** (ração, volumoso, suplementos e vitaminas). Trabalho de Programação Web Avançada II (UVV).

Monorepo com duas partes separadas:

| Pasta | O que é |
|---|---|
| `backend/` | API REST em Flask + SQLAlchemy (SQLite em desenvolvimento) |
| `front-end/` | Interface em Vue 3 (em construção) |

## Configuração

O `.env` fica na raiz do repositório e não vai pro Git. Crie a partir do modelo:

```bash
copy .env.example .env
```

## Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev,test]"
flask db upgrade
pytest -v
flask run
```

Detalhes (banco, seed, migrações, atalhos `invoke`): [backend/README.md](backend/README.md).

## Front-end

Ainda não iniciado.
