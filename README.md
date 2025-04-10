# 💰 MyFinance

### Linguagens
<p>
    <img src="https://img.shields.io/badge/Python-ED8B00?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">
    <img src="https://img.shields.io/badge/HTML-E34F26?style=for-the-badge&logo=html5&logoColor=white">
    <img src="https://img.shields.io/badge/CSS-1572B6?style=for-the-badge&logo=css3&logoColor=white">
</p>

### Frameworks e Bibliotecas Relevantes
<p>
    <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white">
    <img src="https://img.shields.io/badge/Django--REST--Framework-ff1709?style=for-the-badge&logo=django&logoColor=white">
    <img src="https://img.shields.io/badge/JWT--SimpleJWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white">
    <img src="https://img.shields.io/badge/Django--Channels--WebSocket-00BFFF?style=for-the-badge&logo=django&logoColor=white">
    <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white">
    <img src="https://img.shields.io/badge/Blue-1E90FF?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/iSort-ef8336?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/Python_Magic-5319e7?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/Django_Extensions-003B57?style=for-the-badge&logo=django&logoColor=white">
    <img src="https://img.shields.io/badge/Daphne-5E5CFF?style=for-the-badge&logo=fastapi&logoColor=white">
</p>

### Gerenciador de dependências
<p>
    <img src="https://img.shields.io/badge/Poetry-60A5FA?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/Pip-60A5FA?style=for-the-badge&logo=python&logoColor=white">
</p>

### DevOps
<p>
    <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
    <img src="https://img.shields.io/badge/Docker--Compose-1488C6?style=for-the-badge&logo=docker&logoColor=white">
    <img src="https://img.shields.io/badge/Makefile-000000?style=for-the-badge&logo=gnu&logoColor=white">
</p>

### Bancos de Dados e Cache
<p>
    <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white">
    <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white">

</p>

### Outros
<p>
<img src="https://img.shields.io/badge/Insomnia-4000BF?style=for-the-badge&logo=insomnia&logoColor=white">
</p>

**MyFinance** é uma aplicação web desenvolvida com Django para controle financeiro pessoal, focada em organização de gastos, controle patrimonial e inteligência na categorização de transações.

## ✨ Features

### 💰 Gestão Financeira Pessoal
- **Controle completo das finanças**: Gerencie contas, cartões, categorias, subcategorias, lançamentos e parcelamentos com facilidade.
- **Fluxo de caixa mensal**: Visualize os lançamentos consolidados do mês com base nas contas e cartões selecionados.
- **Resumo financeiro**: Indicadores úteis como gastos à vista, no cartão e despesas fixas.
- **Extrato por conta**: Acompanhe o extrato mensal de cada conta cadastrada.
- **Faturas dos cartões**: Visualize as faturas mensais detalhadas de todos os seus cartões de crédito.

### 📊 Dashboards Interativos
- **Despesas por categoria**: Gráfico de barras com ranking das categorias mais gastas. Clique em uma categoria para ver os detalhes por subcategoria.
- **Fluxo de caixa**: Gráfico de rosca que compara a proporção entre receitas e despesas do mês.
- **Receitas por origem**: Gráfico de rosca com a distribuição percentual das suas fontes de receita.
- **Visão de longo prazo**: Gráfico de linha que mostra a evolução de receitas, despesas e investimentos ao longo do tempo, com filtro por ano ou período total. Um gráfico de rosca ao lado permite filtrar a visualização interativa.

### 🧠 Planejamento e Projeções
- **Planejamento de sonhos**: Cadastre objetivos, defina prazos e planeje mensalmente como alcançá-los.
- **Evolução patrimonial** *(em desenvolvimento)*: Controle de ativos como renda fixa, renda variável e criptomoedas.

### 📥 Importações Inteligentes
- **Importação automática de extratos** *(em desenvolvimento)*: Envie seus extratos bancários ou faturas de cartão e deixe que o [Transaction Classifier](https://github.com/fantunesdev/transaction_classifier) cuide da categorização. O modelo de machine learning é personalizado para cada usuário e aprende continuamente com seus feedbacks.


### 📈 Evolução Patrimonial
- **Evolução Patrimonial**: controle de ativos como renda fixa, renda variável e criptomoedas (em desenvolvimento).

## 🧱 Principais Tecnologias

- Python 3.13
- Django
- MySQL
- WebSockets com Redis
- Docker + Docker Compose
- JavaScript (frontend)
- [River](https://riverml.xyz) (aprendizado de máquina online)

## 📁 Estrutura do Projeto

```
myfinance/
├── api/
│   ├── serializers/
│   ├── services/
│   ├── views/
│   └── websockets/
├── login/
│   ├── forms/
│   ├── services/
│   └── templates/
├── statement/
│   ├── forms/
│   │   ├── core/
│   │   ├── dream/
│   │   └── portfolio/
│   │       ├── fixed_income/
│   │       └── variable_income/
│   ├── services/
│   │   ├── base_service.py
│   │   ├── core/
│   │   ├── dream/
│   │   └── portfolio/
│   │       ├── fixed_income/
│   │       └── variable_income/
│   ├── static/
│   │   ├── css
│   │   ├── img
│   │   └── js
│   │   │   ├── data/
│   │   │   ├── layout/
│   │   │   └── pages/
│   ├── templates/
│   ├── templatetags/
│   ├── urls/
│   │   ├── core/
│   │   ├── dream/
│   │   └── portfolio/
│   │       ├── fixed_income/
│   │       └── variable_income/
│   ├── utils/
│   └── views/
│   │   ├── base_view.py
│   │   ├── core/
│   │   ├── dream/
│   │   └── portfolio/
│   │       ├── fixed_income/
│   │       └── variable_income/
├── myfinance/  # settings, wsgi, asgi
├── Makefile
├── manage.py
├── pyproject.toml
└── README.md

```

## ⚙️ Como Rodar Localmente

### Pré-requisitos

- Docker e Docker Compose instalados
- Make (Linux/Mac)

Aplicação para fazer o controle financeiro.

## Instalação

Configure o .env com as seguintes variáveis de ambiente:

> SECRET_KEY  
> HOSTS  
> CORS_ALLOWED_ORIGINS  
> CSRF_TRUSTED_ORIGINS  
> 
> MYSQL_DATABASE  
> MYSQL_HOST  
> MYSQL_PORT  
> DEBUG  
> MYSQL_USER  
> MYSQL_PASSWORD  

Instale a aplicação:

> make install

## Rodando a aplicação

> make run


# Acessar o app no navegador
```
http://localhost:8000
```

### Variáveis de ambiente

As variáveis estão centralizadas no `.env` dentro do repositório de orquestração (fora do `myfinance`), incluindo:
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`
- `SECRET_KEY`, `DEBUG`, etc.

## 🔄 Integração com IA (categorizador de transações)

A aplicação se comunica com o microserviço `transaction_classifier` via API para prever categorias e subcategorias com base na descrição da transação.

Fluxo:
1. Usuário importa ou cria uma transação.
2. A descrição é enviada para o classificador.
3. O classificador retorna `category_id` e `subcategory_id` com base no histórico do usuário.
4. O usuário pode corrigir o resultado, e essa correção pode ser usada para re-treinar o modelo futuramente.

O modelo utiliza **aprendizado online** com a biblioteca **River**, permitindo personalização e atualização contínua sem necessidade de re-treinamento em batch.

## ✅ Testes

Os testes estão sendo estruturados no diretório `tests/` com foco inicial nas transações (`add_installments`, entre outros).

```bash
make test
```

## 🚧 Roadmap

- [x] Refatoração da arquitetura por feature
- [x] WebSocket para atualização dinâmica de categorias
- [x] Suporte a ativos de renda fixa
- [x] Previsão automática de categorias com IA
- [ ] Correção de predições com aprendizado contínuo
- [ ] Módulo de Renda Fixa
- [ ] Módulo de Renda Variável
- [ ] Módulo de Criptomoedas
- [ ] Dashboard visual com gráficos

## 📄 Licença

Este projeto é privado e de uso pessoal. Licenciamento futuro pode ser considerado.

