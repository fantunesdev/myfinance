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

As instruções completas de instalação, permissões, variáveis, recuperação e
limites estão em `deploy/README.md` no repositório
[`fantunesdev/docker`](https://github.com/fantunesdev/docker/blob/main/deploy/README.md).
Consulte a revisão fixada em `MYFINANCE_INFRA_REF` para obter as instruções
correspondentes ao pipeline instalado.
