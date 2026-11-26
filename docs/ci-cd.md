# CI/CD

O workflow `.github/workflows/myfinance.yml` executa os testes Python e
JavaScript, valida a infraestrutura e constrói a imagem de produção em pull
requests para `main`. Pushes na `main` publicam a imagem no GHCR e podem
acionar o deploy blue/green na VM pela rede local.

Configure `MYFINANCE_INFRA_REF` com o SHA completo da infraestrutura. O deploy
fica desabilitado até configurar `MYFINANCE_DEPLOY_ENABLED=true` e cadastrar o
runner com label `myfinance-deploy`, acesso SSH à VM e o environment
`production`. O deploy usa a imagem aprovada por digest e SHA; não constrói
outro código no servidor.

A stack usa Python 3.15.2, Django 6.1.3, Poetry 2.5.2 e Node 26.13.1 LTS.
A CI instala os dois lockfiles e executa a suíte Python tanto com SQLite quanto
com MySQL 8.4 temporário. O envio de e-mail usa `MAILERS` do Django 6.1,
preservando as variáveis de ambiente `EMAIL_BACKEND` e `EMAIL_TIMEOUT`.

Para publicar a atualização da stack, versione primeiro os Dockerfiles
atualizados no repositório de infraestrutura e ajuste `MYFINANCE_INFRA_REF`
para esse SHA antes de executar a CI do MyFinance. Os Dockerfiles de produção
e desenvolvimento precisam usar Python 3.15.2 e Poetry 2.5.2. Apenas reiniciar
os containers não instala as dependências novas; reconstrua as imagens.
Faça backup do banco e preserve o digest da imagem anterior para reversão.
Esta atualização não exige novas migrações dos modelos da aplicação; ainda
é necessário aplicar as migrações pendentes das bibliotecas atualizadas.

As instruções completas de instalação, permissões, variáveis, recuperação e
limites estão em `deploy/README.md` no repositório
[`fantunesdev/docker`](https://github.com/fantunesdev/docker/blob/main/deploy/README.md).
Consulte a revisão fixada em `MYFINANCE_INFRA_REF` para obter as instruções
correspondentes ao pipeline instalado.
