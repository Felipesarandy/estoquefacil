# EstoqueFácil — back-end de controle de estoque para equinos

## Objetivo e conteúdo da entrega

Controlar entradas, consumo, perdas e contagens físicas e avisar quando um produto atingir seu ponto de reposição, considerando consumo médio, prazo de entrega e margem de segurança. Não realiza compras nem possui rotas de pedidos.

Este pacote contém código, migrações, testes automáticos e instruções. Não contém banco de demonstração, usuários de exemplo, saldos fictícios nem comandos `seed`/`seed-equinos`. A criação do app não cadastra produtos automaticamente. O colega responsável pelo banco deve configurar a conexão oficial, compatibilizar a estrutura e cadastrar os dados uma única vez.

## 1. Configurar a conexão do grupo

Copie `.env.example` para `.env`. Configure `DATABASE_URL` com a conexão real usada pelo grupo e as chaves SECRET_KEY/JWT_SECRET_KEY. Não publique credenciais. O padrão `sqlite:///dev.db` corresponde a `instance/dev.db` neste projeto; não significa que um banco oficial já esteja entregue.

Uma variável DATABASE_URL definida no terminal tem prioridade sobre o `.env`. Se ela ainda aponta para o banco de demonstração, remova-a antes de iniciar o app:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
```

Esse comando remove apenas a variável do terminal, não o arquivo do banco. O arquivo de demonstração que já existe no computador do usuário não é apagado ao extrair o ZIP. Para removê-lo, pare o servidor e, na pasta do projeto antigo, execute somente:

```powershell
Remove-Item .\instance\teste_equinos.db -ErrorAction SilentlyContinue
```

Não apague o banco oficial nem copie um banco vazio por cima dele.

## 2. Estrutura que o responsável pelo banco deve conferir

Preservar as tabelas originais `stores`, `users`, `categories`, `suppliers`, `products`, `stock_movements` e `inventory_counts`. Usar as chaves estrangeiras e tipos definidos em `app/models.py`.

### Produtos (`products`)

| Campo | Finalidade |
|---|---|
| id, store_id | Identificação e separação dos dados por loja |
| category_id, supplier_id | Categoria e fornecedor (fornecedor opcional) |
| name, code, unit | Nome, SKU e unidade; código único por loja |
| cost_price, sale_price | Valores monetários, Numeric(10,2) |
| current_stock | Saldo, Numeric(10,3), nunca negativo |
| min_stock, max_stock | Mínimo manual e máximo opcional |
| active | Produto disponível para uso |

Saldo deve ser alterado por movimentações e contagem física, não por edição direta do cadastro. Preços e fornecedores reais devem ser informados pelo grupo; os valores iniciais zero não representam preços de mercado.

### Parâmetros de reposição (`replenishment_policies`)

| Campo | Tipo | Regra |
|---|---|---|
| product_id | Integer, PK/FK para products.id | Uma política por produto |
| weekly_consumption | Numeric(10,3) | Consumo agregado semanal, maior que zero |
| lead_days | Integer | Prazo de entrega em dias corridos, de 0 a 3650 pela API |
| safety_days | Integer | Margem em dias, de 0 a 3650 pela API |

Compatibilidade: o campo legado `order_quantity` continua no esquema com valor padrão 1 no modelo; não é recebido nem retornado pela API e não participa do cálculo. Não deve ser usado pelo front-end.

As migrações históricas ainda contêm `purchase_orders`, e o modelo `LegacyPurchaseOrder` preserva compatibilidade e registros antigos. Essa tabela está sem uso: não cadastrar pedidos, não consultá-la para calcular saldo e não integrar com front-end. Mantê-la evita apagar dados ou reescrever o histórico de migrações de quem instalou versões anteriores.

### Movimentações e auditoria

`stock_movements` registra produto, usuário, tipo (entrada/saida), motivo, quantidade positiva, custo unitário na data, observação e data. Consumo: `uso_interno`; perdas: `avaria`, `vencimento`, `furto`. A saída é bloqueada quando excede o saldo.

`inventory_counts` registra produto, responsável, saldo do sistema, quantidade contada e data. A diferença é quantidade contada menos saldo do sistema; o ajuste gera movimentação e atualiza o saldo na mesma transação. Somente administrador registra contagens.

## 3. Itens e parâmetros a cadastrar

Criar ou reutilizar categorias Alimentação, Produtos veterinários e Higiene. O comando usa os nomes sem acentos abaixo para manter os identificadores já empregados no código. Não há curativos.

| SKU | Nome no código | Categoria | Unidade | Consumo por semana | Entrega | Margem | Segurança calculada | Ponto de reposição |
|---|---|---|---|---:|---:|---:|---:|---:|
| EQ001 | Vermifugo equino | Produtos veterinarios | un | 10 | 5 dias | 2 dias | 3 un | 11 un |
| EQ002 | Racao equina | Alimentacao | kg | 140 | 5 dias | 2 dias | 40 kg | 140 kg |
| EQ003 | Feno | Alimentacao | kg | 70 | 3 dias | 2 dias | 20 kg | 50 kg |
| EQ004 | Sal mineral para equinos | Alimentacao | kg | 7 | 5 dias | 2 dias | 2 kg | 7 kg |
| EQ005 | Shampoo para equinos | Higiene | un | 2 | 4 dias | 2 dias | 1 un | 3 un |
| EQ006 | Produto para controle de carrapatos | Produtos veterinarios | un | 2 | 5 dias | 2 dias | 1 un | 3 un |

Os valores são hipóteses logísticas acordadas para o trabalho, não medições reais, doses ou recomendações por animal. Ajustar ao consumo real quando houver dados. O cadastro não prescreve medicamentos nem define frequência de aplicação.

**Saldo inicial:** novos itens são cadastrados com zero. O grupo deve fazer a contagem real e registrar a entrada correspondente. Não carregar os antigos saldos fictícios de 10 unidades, 200 kg ou 100 kg como se fossem reais.

Se já houver um produto com o mesmo SKU e nome diferente, duplicidade de nome, unidade diferente ou produto inativo, o comando cancela a transação para o responsável resolver o conflito. Produtos com nomes da versão antiga, como `Vermifugo equino (exemplo)`, devem ser revisados antes de reutilizar um banco anterior. Não renomear ou sobrescrever automaticamente registros reais.

## 4. Instalação e aplicação no banco

Na pasta do projeto, PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Para PostgreSQL, instale também `.[postgres]`. Antes de executar migrações, faça backup e confirme que a conexão aponta para o banco correto.

```powershell
.\.venv\Scripts\python.exe -m flask --app backend_app db upgrade
```

Histórico fornecido: `d2b9e292d1e5` (estrutura original) → `equine_replenishment` (estrutura adicional). Se o banco do colega já usa outro histórico ou estrutura, ele deve compatibilizar a migração; não usar `stamp` para fingir que uma migração foi aplicada, nem recriar tabelas preenchidas.

É necessário existir uma loja e seu usuário administrador. Reutilize o cadastro do grupo. Em banco vazio, use POST `/api/auth/register`, com `store_name`, `name`, `email`, `password`, para criar a loja e o administrador. Não há conta de demonstração incluída. Use o `store_id` do usuário autenticado, retornado em `/api/auth/me`.

Depois, cadastrar os seis itens:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend_app cadastrar-equinos --store-id ID_DA_LOJA
```

Substitua ID_DA_LOJA pelo número real. O comando não cria lojas ou usuários, não apaga dados e não altera saldos, preços ou políticas já existentes. Adiciona itens e políticas faltantes na loja escolhida. Pode ser repetido sem duplicar os produtos. Não é necessário executar ao abrir o sistema.

Para iniciar:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend_app run --debug
```

## 5. Regras de estoque e integração com front-end

- Consumo diário = consumo semanal / 7.
- Estoque de segurança = consumo diário × margem, arredondado para cima.
- Ponto de reposição = consumo diário × prazo de entrega + segurança, arredondado para cima.
- Unidades/caixas: arredondar para inteiro. kg/l/m: para 0,001.
- Avisar reposição quando saldo <= ponto de reposição.
- Risco de ruptura quando saldo < consumo diário × prazo de entrega.
- Cobertura estimada = saldo / consumo diário.
- O passar dos dias não desconta estoque automaticamente; cada uso real precisa de uma saída.

Exemplo: feno com saldo de 45 kg e ponto de 50 kg retorna `reorder_needed: true`. O sistema avisa o responsável; não realiza compra. Quando o produto chegar de fato, registrar entrada.

| Rota | Finalidade |
|---|---|
| POST /api/auth/login | Obter token JWT |
| GET /api/products | Listar itens e saldos |
| PUT /api/products/ID/replenishment-policy | Administrador define consumo, prazo e margem |
| GET /api/replenishment | Planejamento, cobertura, ponto e alertas |
| GET /api/alerts | Produtos no ponto de reposição (ou mínimo manual quando sem política) |
| POST /api/movements | Entrada, consumo ou perda real |
| GET /api/movements | Histórico auditável |
| POST /api/inventory-counts | Contagem física e ajuste pelo administrador |

Rotas de dados usam `Authorization: Bearer TOKEN`. O campo `is_low_stock` usa o cálculo da política quando existente; sem política usa `min_stock`. `reorder_needed` permite exibir o aviso de reposição no front-end. Não há envio de notificações externas.

Exemplo de configuração:

```json
{"weekly_consumption":10,"lead_days":5,"safety_days":2}
```

Exemplo de entrada real (substituir o ID e a quantidade):

```json
{"product_id":1,"type":"entrada","reason":"compra","quantity":10,"note":"Quantidade efetivamente recebida"}
```

Não estão implementados calendário clínico por animal nem rastreio por lote/validade.

## 6. Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testes automáticos usam SQLite temporário em memória e não precisam do banco oficial. Cobrem cálculos, alertas consistentes, saldo insuficiente, isolamento entre lojas e cadastro sem duplicação ou sobrescrita. Esses testes são diferentes do arquivo de demonstração removido.
