# MyFinance

MyFinance e uma aplicacao web completa para controle financeiro pessoal, criada como produto real e tambem como projeto de portfolio. A ideia e resolver um problema do dia a dia com uma arquitetura de aplicacao profissional: dominio financeiro rico, regras de negocio, dashboards interativos, importacao automatizada de dados, API, WebSocket, autenticacao, Docker e integracao com um microservico de classificacao inteligente de transacoes.

Mais do que um CRUD, este projeto demonstra minha capacidade de transformar uma necessidade pessoal em um sistema robusto, evolutivo e operavel. Ele cobre desde a modelagem do dominio e organizacao do backend ate experiencia de uso, automacoes, integracoes externas, visualizacoes que geram insights e preocupacoes de deploy.

## O que este projeto demonstra

- Modelagem de um dominio financeiro com contas, cartoes, faturas, categorias, parcelamentos, sonhos, emprestimos e investimentos.
- Backend Django organizado por apps, services, forms, views, templates, serializers e comandos de manutencao.
- APIs REST autenticadas com Django REST Framework, JWT, OAuth2 e token de dispositivo.
- Arquitetura ASGI com Django Channels, Redis e WebSocket.
- Integracao entre sistemas por HTTP, incluindo um microservico FastAPI separado que treina modelos por usuario para classificar lançamentos financeiros de acordo com os hábitos e correções do proprio usuário.
- Importacao configuravel de arquivos e notificacoes capturadas automaticamente no celular via Tasker, com revisao supervisionada pelo usuario antes de virar lancamento.
- Dashboards interativos que permitem explorar os dados por mes, ano, categoria, subcategoria, receitas, despesas e investimentos.
- Ambiente conteinerizado com Docker Compose, Nginx, MySQL, Redis e servico de IA.
- Testes Python e JavaScript cobrindo partes criticas do comportamento.

## Destaques tecnicos

- Separacao entre regras de negocio e camada de apresentacao usando services dedicados.
- Usuario customizado e regras de visibilidade por dono, dependente e numero de cartao.
- Configuracoes por usuario para controlar exibicao de dados em graficos e tela inicial.
- Visualizacao analitica pensada para gerar insights: graficos clicaveis, drill-down de categorias para subcategorias e tabelas detalhadas a partir dos pontos de interesse.
- Fluxo de feedback para melhorar a categorizacao automatica e a normalizacao das descricoes dos lancamentos.
- Suporte a operacao local e conteinerizada, com comandos de manutencao e logs rotativos.
- Evolucao incremental: o projeto tem modulos legados preservados e modulos novos, como o app dedicado de investimentos, convivendo na mesma base.

## Funcionalidades entregues

### Controle financeiro

- Lancamentos de entrada e saida com data de lancamento, data de pagamento, conta, cartao, categoria, subcategoria, moeda, observacao e status de efetivacao.
- Despesas a vista, despesas no cartao, receitas, despesas fixas, lancamentos anuais e lancamentos recorrentes.
- Parcelamentos com geracao e acompanhamento de parcelas.
- Busca de lancamentos por descricao e navegacao mensal/anual.
- Configuracao de lancamentos que aparecem na tela inicial por conta, cartao ou numero de cartao.
- Modo "proximo mes", que antecipa a visao mensal a partir de um dia configurado no perfil.

### Contas, cartoes e cadastros base

- Bancos, tipos de conta, contas, bandeiras, cartoes e numeros de cartao.
- Cartoes com dia de fechamento, dia de vencimento, limite, cartao pre-pago e associacao opcional a conta.
- Numeros de cartao com nome, ultimos digitos, visibilidade na tela inicial, usuario dependente e lista de usuarios com permissao de visualizacao.
- Categorias e subcategorias de entrada/saida.
- Configuracao por usuario de quais subcategorias aparecem em graficos mensais e anuais.

### Extratos, faturas e dashboards

- Tela inicial com resumo do mes atual ou do mes antecipado pela configuracao de perfil.
- Consolidacao de receitas, despesas, saldo, gastos em cartao, gastos a vista e despesas fixas.
- Extrato por conta e fatura por cartao.
- Dashboards com filtros de ano/mes e graficos consumidos pelo frontend JavaScript.
- Graficos clicaveis para investigar gastos por categoria e abrir a visao por subcategoria.
- Alternancia entre grafico de barras por categoria e grafico de linha acumulado ao longo do mes.
- Demonstrativo anual com linha temporal e donut clicavel para alternar entre receitas, despesas e investimentos.
- Overview anual para comparar a evolucao entre anos e perceber tendencias de longo prazo.
- Tabelas detalhadas geradas a partir do clique em categorias/subcategorias, ajudando o usuario a sair do insight visual para os lancamentos que explicam aquele numero.
- Configuracoes para ocultar subcategorias especificas de graficos de fluxo de caixa, relatorio anual, barras por categoria e linhas mensais.

### Importacao de transacoes

- Importacao de lancamentos por arquivo.
- Configuracoes reutilizaveis de CSV por usuario.
- Importacao de JSON gerado pelo Tasker, com uma notificacao por linha.
- Mapeamento configuravel de colunas de data, descricao, valor e parcela.
- Suporte a importacao para lancamentos financeiros e movimentacoes de investimento.
- Formatos de parcela automatico, `x/y` e `x-y`.
- Associacao da importacao a conta ou cartao.
- Campos de comparacao configuraveis para auxiliar conciliacao/duplicidade.

### Notificacoes

- Captura automatica de notificacoes bancarias no celular usando Tasker.
- Envio das notificacoes para o MyFinance pela API, mantendo app, titulo, mensagem e data original.
- Importacao supervisionada: o sistema sugere os lancamentos, mas o usuario revisa, ajusta categoria/subcategoria/descricao e escolhe o que sera cadastrado.
- Identificacao automatica do cartao a partir do aplicativo de origem, usuario e ultimos digitos encontrados na mensagem.
- Preferencias por titulo de notificacao, permitindo ativar ou desativar quais tipos entram no fluxo de importacao.
- Comando de manutencao para vincular notificacoes a cartoes existentes.

### Classificacao inteligente

- Cliente HTTP para o microservico `transaction_classifier`, construido com FastAPI e River.
- Modelos separados por usuario, treinados com categorias, subcategorias, historico real de lancamentos e feedbacks de correcao.
- Predicao de categoria e subcategoria com base na descricao do lancamento e, quando disponivel, na categoria informada.
- Sugestao de descricao tratada a partir de correcoes anteriores do usuario, ajudando a padronizar nomes recorrentes como compras, estabelecimentos e notificacoes bancarias.
- Retreinamento por feedback, dando peso maior para correcoes reais feitas pelo usuario.
- Flag administrativa para habilitar/desabilitar a integracao com o classificador.

### Sonhos e metas

- Cadastro de sonhos/objetivos financeiros com valor alvo, data limite, data de conclusao, status e anotacoes.
- Lancamentos associados a sonhos.
- Calculo de valor atual, valor restante e percentual de progresso.
- Parcelas planejadas para cada sonho.

### Emprestimos

- Cadastro de emprestimos com status ativo/finalizado e anotacoes.
- Lancamentos de emprestimo com data, descricao e valor.
- Acompanhamento do saldo a partir dos lancamentos vinculados.

### Investimentos

O projeto tem dois conjuntos de funcionalidades de investimento.

No app `investments`:

- Dashboard de investimentos.
- Corretoras, bancos, exchanges, carteiras e outros brokers.
- Ativos de renda fixa, renda variavel, cripto, moeda e outros.
- Investimentos com ativo, broker, data inicial, vencimento, status e anotacoes.
- Movimentacoes de aporte, resgate, rendimento/provento, atualizacao de valor e custos.
- Quantidade, preco unitario, valor atual e vencimento por movimentacao.
- Carteira padrao e fluxos de aplicar a partir da carteira ou resgatar para a carteira.
- Vinculo opcional entre movimentacao de investimento e lancamento financeiro.

No modulo de carteira do app `statement`:

- Indices financeiros, como CDI ou SELIC, com codigo do Banco Central.
- Serie historica de indices.
- Tipos de titulo de renda fixa, como CDB, LCI ou Tesouro.
- Ativos de renda fixa com principal, data de investimento, vencimento, indice e taxa contratada.
- Tickers, setores, ativos de renda variavel e transacoes de compra/venda.

### Usuarios, autenticacao e perfil

- Usuario customizado com `username`, nome, email, foto, permissoes e status.
- Perfil com configuracao de proximo mes e rastreamento de combustivel.
- Login web por sessao.
- API com autenticacao por sessao, JWT, OAuth2 e token de dispositivo.
- Comando interativo para criacao de usuario staff.
- Comando para criar uma aplicacao OAuth2 usada pelo Transaction Classifier.

### API e WebSocket

- API REST em `/api/` usando Django REST Framework.
- Endpoints para categorias, subcategorias, feedbacks de categorizacao, contas, bancos, cartoes, notificacoes, transacoes, investimentos e movimentacoes de investimento.
- JWT em `/api/token/`, refresh em `/api/token/refresh/` e validacao em `/api/validate-token/`.
- Endpoints do classificador em `/api/transaction-classifier/`.
- Endpoint de progressao de renda fixa em `/api/fixed-income/progression/`.
- WebSocket via Django Channels, Redis e ASGI.

## Stack

- Python 3.13
- Django 4.2
- Django REST Framework
- Django Channels, Daphne e Redis
- MySQL como banco principal
- PostgreSQL configurado como banco secundario
- OAuth2 Toolkit e Simple JWT
- Poetry
- JavaScript, CSS e templates Django
- Pytest, pytest-django, Blue, isort, ESLint e Prettier
- Docker, Docker Compose e Nginx no repositorio de orquestracao

## Decisoes de arquitetura

O MyFinance foi construido para crescer por modulos. O app `statement` concentra o core financeiro, o app `investments` isola a evolucao da carteira de investimentos, o app `login` mantem usuario/perfil/autenticacao e o app `api` expoe os recursos para consumo externo.

As regras de negocio ficam majoritariamente em services, evitando concentrar tudo em views ou forms. Essa escolha deixa os fluxos mais testaveis e facilita reutilizar comportamento entre interface web, API e comandos de manutencao.

O projeto tambem separa a classificacao inteligente em um microservico proprio. Assim, o sistema financeiro continua responsavel pelo dominio e pela persistencia, enquanto o classificador pode evoluir de forma independente.

## Estrutura do Projeto

```text
myfinance/
|-- api/                    # API REST, serializers, views, services e websockets
|-- clients/                # Clientes HTTP para microservicos externos
|-- investments/            # Investimentos, ativos, brokers e movimentacoes
|-- login/                  # Usuario customizado, perfil, login e comandos de auth
|-- myfinance/              # Settings, URLs, WSGI e ASGI
|-- statement/              # Core financeiro, dashboards, carteira, sonhos e emprestimos
|-- tests/                  # Testes Python
|-- package.json            # Ferramentas JS
|-- pyproject.toml          # Dependencias Python e config do Poetry
`-- Makefile                # Comandos de instalacao, execucao e formatacao
```

O ambiente Docker usado para rodar a aplicacao fica em outro repositorio local:

```text
/home/fernando/git/dev/docker/
|-- docker-compose.yml
|-- Dockerfile
|-- nginx/
|-- myfinance/              # Copia/checkout do app
`-- transaction_classifier/ # Microservico de classificacao
```

## Variaveis de Ambiente

A aplicacao carrega variaveis via `.env`/ambiente. As principais sao:

```env
SECRET_KEY=
DEBUG=
HOSTS=
CORS_ALLOWED_ORIGINS=
CSRF_TRUSTED_ORIGINS=
ENVIRONMENT=

ALGORITHM=
ACCESS_TOKEN_EXPIRE_MINUTES=
CLIENT_SECRET=

MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_HOST=
MYSQL_PORT=

POSTGRESQL_DATABASE=
POSTGRESQL_USER=
POSTGRESQL_PASSWORD=
POSTGRESQL_HOST=
POSTGRESQL_PORT=

TRANSACTION_CLASSIFIER_URL=
TRANSACTION_CLASSIFIER_PORT=
```

No repositorio Docker, essas variaveis sao expostas com prefixos como `MYFIN_` e `TRANSACTION_CLASSIFIER_` no `docker-compose.yml`.

## Rodando com Docker

O fluxo principal de execucao fica no repositorio `/home/fernando/git/dev/docker`.

1. Garanta que o repositorio `myfinance` esteja disponivel dentro da pasta raiz do Docker, como `./myfinance`.
2. Crie o `.env` do Docker com as variaveis usadas no `docker-compose.yml`.
3. Inclua o host local desejado em `/etc/hosts`, por exemplo:

```text
127.0.0.1 myfinance.com
```

4. Suba os containers:

```bash
docker compose up --build
```

Servicos principais:

- `app-myfin`: Django/ASGI com Daphne.
- `mysql-myfin`: banco MySQL.
- `redis-myfin`: Redis para cache/camadas de canal.
- `nginx-myfin`: proxy HTTPS local, arquivos estaticos e media.
- `transaction-classifier`: microservico de classificacao de transacoes.

O Nginx publica HTTPS local na porta `81` do host. Em desenvolvimento, acesse:

```text
https://localhost:81
```

ou configure um proxy externo para encaminhar seu dominio local para `https://127.0.0.1:81`.

## Rodando Localmente sem Docker

Pre-requisitos:

- Python 3.13
- Poetry
- MySQL acessivel
- Redis acessivel para recursos de WebSocket/cache
- Node.js/npm para formatacao dos arquivos JavaScript

Instale as dependencias:

```bash
poetry install
npm install
```

Configure o `.env` na raiz do projeto com as variaveis listadas acima.

Rode as migracoes e colete estaticos:

```bash
poetry run python manage.py migrate
poetry run python manage.py collectstatic
```

Crie um usuario staff interativamente:

```bash
poetry run python manage.py create_user
```

Suba a aplicacao:

```bash
poetry run daphne -b 0.0.0.0 -p 8765 myfinance.asgi:application
poetry run python manage.py runserver
```

Tambem existem atalhos no `Makefile`:

```bash
make install
make run
make update
make format
make create_oauth_app
```

## Rotas Web Principais

- `/`: lancamentos do mes atual.
- `/login/` e `/logout/`: autenticacao web.
- `/relatorio_financeiro/`: lancamentos, importacoes, configuracoes e dashboards.
- `/relatorio_financeiro/configuracoes/`: cadastros administrativos.
- `/relatorio_financeiro/dashboards/`: dashboards financeiros.
- `/carteira/`: carteira/renda fixa/renda variavel do modulo `statement`.
- `/investimentos/`: dashboard e CRUDs do app `investments`.
- `/emprestimos/`: emprestimos.
- `/sonhos/`: sonhos e parcelas.
- `/usuarios/`: usuarios e perfil.
- `/admin/`: Django Admin.

## API

A API fica em `/api/` e exige usuario autenticado por padrao.

Recursos registrados:

- `/api/categories/`
- `/api/subcategories/`
- `/api/categorization-feedback/`
- `/api/accounts/`
- `/api/banks/`
- `/api/cards/`
- `/api/notifications/`
- `/api/transactions/`
- `/api/transaction-classifier/`
- `/api/investments/`
- `/api/investment-transactions/`

Autenticacao:

```text
POST /api/token/
POST /api/token/refresh/
GET  /api/validate-token/
```

Tambem ha uma collection do Insomnia em:

```text
api/docs/insomnia_collection.json
```

## Transaction Classifier

A integracao com IA usa o cliente em `clients/transaction_classifier/` e conversa com um microservico FastAPI separado, mantido no repositorio `/home/fernando/git/dev/transaction_classifier`.

Esse microservico usa River para aprendizado incremental e trabalha com modelos isolados por usuario. Na pratica, o MyFinance continua sendo o sistema de origem dos dados e o classificador aprende com o historico financeiro daquele usuario: categorias, subcategorias, descricoes de lancamentos e feedbacks de correcao.

Ele possui dois fluxos principais:

- `SubcategoryPredictor`: aprende com subcategorias e lancamentos reais para prever categoria e subcategoria a partir da descricao.
- `DescriptionPredictor`: aprende com feedbacks onde o usuario corrigiu descricoes, criando um historico de padronizacao para sugerir descricoes mais limpas e consistentes.

O servico espera as seguintes variaveis no MyFinance:

```env
TRANSACTION_CLASSIFIER_URL=
TRANSACTION_CLASSIFIER_PORT=
```

Fluxo geral:

1. O usuario cria/importa uma transacao ou importa notificacoes capturadas pelo Tasker.
2. A descricao e enviada ao microservico com o token do usuario.
3. O modelo do usuario retorna categoria, subcategoria e, quando houver confianca, uma descricao sugerida.
4. O usuario revisa a sugestao antes de cadastrar ou corrigir o lancamento.
5. Correcoes geram feedbacks que podem retreinar os modelos e melhorar as proximas sugestoes.

Para integracao OAuth2 do microservico, crie o usuario `transaction-classifier` e rode:

```bash
poetry run python manage.py create_oauth_app
```

## Comandos de Manutencao

```bash
poetry run python manage.py create_user
poetry run python manage.py create_oauth_app
poetry run python manage.py backfill_home_screen
poetry run python manage.py link_notifications_to_cards
```

## Testes e Qualidade

Testes Python:

```bash
poetry run pytest
```

Testes JavaScript existentes:

```bash
node --test tests/js/*.test.mjs
```

Formatacao:

```bash
make format
```

O `make format` executa `isort`, `blue` e `prettier` nos arquivos JavaScript de `statement/static/js/`.

## Observacoes de Operacao

- O projeto usa `AUTH_USER_MODEL = login.User`; aplique migracoes antes de criar usuarios.
- O Redis configurado em Docker usa o host `redis-myfin` para Channels.
- O Nginx do Docker tambem serve `/static/`, `/media/` e faz upgrade para `/ws/`.
- As configuracoes administrativas sao restritas a usuarios `is_staff`.
- Arquivos enviados e imagens ficam em `MEDIA_ROOT`.
- Logs da aplicacao sao gravados em `logs/myfinance.log` com rotacao diaria.
