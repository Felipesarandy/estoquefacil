from invoke import task


@task
def install(c):
    """Instala o projeto com dependências de desenvolvimento e teste."""
    c.run('pip install -e ".[dev,test]"', echo=True)


@task
def migrate(c, msg="atualizacao"):
    """Gera uma nova migração a partir dos models."""
    c.run(f'flask db migrate -m "{msg}"', echo=True)


@task
def upgrade(c):
    """Aplica as migrações no banco."""
    c.run("flask db upgrade", echo=True)


@task
def seed(c):
    """Popula o banco com dados de exemplo."""
    c.run("flask seed", echo=True)


@task
def test(c):
    """Executa os testes automatizados."""
    c.run("pytest -v", echo=True)
