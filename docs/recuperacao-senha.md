# Recuperação de senha pelo Gmail

O MyFinance oferece recuperação em **Login → Esqueci minha senha** para contas
ativas com senha local. As mensagens são enviadas por uma conta remetente da
aplicação, autorizada na Gmail API. O login Google dos usuários não precisa de
novas permissões.

## Configurar o Google

1. Abra o projeto do MyFinance no [Google Cloud Console](https://console.cloud.google.com/).
2. Em **APIs e serviços → Biblioteca**, procure **Gmail API** e habilite.
3. Em **Google Auth Platform → Clientes**, crie um cliente OAuth do tipo
   **Aplicativo da Web**, por exemplo `MyFinance envio de e-mails`. Mantenha o
   cliente existente do login social separado.
4. Em **URIs de redirecionamento autorizados**, cadastre exatamente:

   ```text
   http://localhost:8766/oauth/gmail/callback/
   ```

   Esse callback pertence ao comando local de autorização, não ao servidor Django
   nem ao callback do login social. Para usar outra porta, altere o cadastro e
   passe a mesma porta em `--port` ao comando.

   Exemplo de endereço para uma autorização hospedada no seu domínio:

   ```text
   https://seu-dominio.com/oauth/gmail/callback/
   ```

   Esse segundo endereço é apenas uma referência de formato: o comando atual
   atende somente em `localhost` e a aplicação ainda não implementa um callback
   Gmail hospedado. Cadastrar esse endereço no Google, sozinho, não o torna
   funcional. Para a implementação atual, autorize localmente e configure o
   refresh token resultante na produção; o domínio público da aplicação fica em
   `PUBLIC_BASE_URL=https://seu-dominio.com`.
5. Em **Acesso a dados**, adicione somente o escopo de envio:

   ```text
   https://www.googleapis.com/auth/gmail.send
   ```

6. Em **Público-alvo**, durante os testes, adicione como usuário de teste a conta
   Gmail que enviará os e-mails do MyFinance.
7. Baixe o JSON do cliente Web após salvar o callback. Guarde-o fora do repositório.

O escopo `gmail.send` é sensível. Confira as exigências de consentimento e
verificação aplicáveis antes da liberação. Projetos externos com status **Teste**
emitem refresh tokens para Gmail que expiram em sete dias; planeje a publicação e
verificação aplicáveis e gere uma autorização adequada ao uso contínuo. Publicar
não elimina as outras causas de revogação, como troca de senha da conta remetente.
Fontes: [escopos Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes)
e [expiração OAuth](https://developers.google.com/identity/protocols/oauth2#expiration).

## Autorizar a conta remetente

Na sua máquina local, onde o navegador está aberto, instale as dependências do
projeto e execute:

```bash
mkdir -p ~/.config/myfinance
poetry run python manage.py authorize_gmail \
  --client-file /caminho/cliente-gmail.json \
  --output ~/.config/myfinance/gmail-token.json
```

Abra no navegador o endereço exibido pelo comando. Escolha **somente a conta
remetente** do MyFinance e autorize o envio. O comando espera por até cinco
minutos, valida o estado da autorização e grava apenas o refresh token, em JSON,
com permissão `600`. Ele não imprime o token nem envia e-mails.

O comando abre um callback apenas no loopback da máquina local. Não o execute
no container web esperando que a porta 8766 do seu navegador alcance o container.
Use o ambiente Python local. Ele precisa conseguir acessar os endpoints OAuth do
Google. Um arquivo de saída existente não é sobrescrito: para reautorizar,
escolha outro caminho e atualize a configuração de produção.

## Configurar o ambiente de produção

No `.env` usado pelo Compose de produção, configure:

```dotenv
PUBLIC_BASE_URL=https://seu-dominio.com
CACHE_URL=redis://redis-myfin:6379/1
EMAIL_BACKEND=login.email_backend.GmailBackend
GMAIL_SENDER_EMAIL=remetente@gmail.com
DEFAULT_FROM_EMAIL="MyFinance <remetente@gmail.com>"
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
PASSWORD_RESET_TIMEOUT=1800
EMAIL_TIMEOUT=15
PASSWORD_RESET_RATE_WINDOW=900
PASSWORD_RESET_IP_LIMIT=30
PASSWORD_RESET_EMAIL_LIMIT=3
```

Use o ID e o segredo do **cliente de envio** e o valor `refresh_token` do JSON
privado gerado pelo comando. Edite o arquivo ou o gerenciador de segredos sem
colar os valores em comandos registrados no histórico. Não envie credenciais no
chat e não versione o JSON nem o `.env`.

`GMAIL_SENDER_EMAIL` deve ser a conta autorizada, ou um alias já autorizado pelo
Gmail. O endereço de `DEFAULT_FROM_EMAIL` precisa corresponder a ele.
`PUBLIC_BASE_URL` deve ser somente a origem pública, sem caminho, query ou
credenciais; fora de `DEBUG`, HTTPS é obrigatório. Os links não usam o host
recebido na requisição.

Como alternativa ao valor em ambiente, configure `GMAIL_REFRESH_TOKEN_FILE` com
um JSON privado acessível ao processo. No Docker é necessário montar esse arquivo
explicitamente, como volume somente leitura ou secret; os arquivos da máquina
host não ficam disponíveis automaticamente. Não é necessário configurar esse
campo quando usar `GMAIL_REFRESH_TOKEN`.

## Publicar e executar o envio

Atualize os repositórios MyFinance e Docker e use o fluxo normal `mfupdate`.
A migração `login.0008` cria a fila. O Compose inclui o serviço
`password-reset-email`, e o deploy o fixa na mesma imagem da aplicação e o recria
após a troca do slot. As variáveis são repassadas ao web e ao worker.

Para uma instalação sem Compose, execute as migrações e mantenha este processo
supervisionado, além do servidor web:

```bash
poetry run python manage.py migrate
poetry run python manage.py process_password_reset_emails
```

Para processar no máximo um item e encerrar:

```bash
poetry run python manage.py process_password_reset_emails --once
```

O backend Gmail renova o access token quando necessário. Falhas têm até três
tentativas, com espera crescente. A fila recupera itens após queda do worker,
descarta solicitações com mais de 30 minutos na configuração padrão e remove
itens concluídos. Uma falha de rede após o Gmail aceitar uma mensagem pode gerar
uma entrega duplicada; o token continua sendo de uso único.

O worker não guarda links, tokens ou endereços de e-mail na fila. Ele valida um
resumo das credenciais atuais antes de enviar, para descartar solicitações antigas
se a senha, e-mail ou último login mudar. Por isso, reiniciar uma solicitação após
entrar novamente pode ser necessário.

## Regras de acesso e limites

Contas inativas, inexistentes, ambíguas ou sem senha utilizável recebem a mesma
resposta pública e não recebem mensagem. Contas exclusivamente Google usam o
Google para entrar e confirmar a primeira senha no perfil.

A janela padrão é de 15 minutos, com até três solicitações por e-mail e 30 por IP.
As chaves no Redis usam HMAC e não contêm os endereços em texto aberto. O código
usa `REMOTE_ADDR` e não confia em `X-Forwarded-For` fornecido pelo cliente. Se o
servidor de aplicação enxergar apenas o IP do proxy, o limite por IP será
compartilhado; ajuste o limite ou a identificação do IP no servidor confiável,
sem aceitar cabeçalhos arbitrários da internet. Falha no cache bloqueia novos
envios e mantém a resposta pública genérica.

Links expiram em 30 minutos, por padrão. A troca de senha invalida os links e as
sessões web anteriores. Não ocorre login automático. As associações Google e a
preferência de login social são preservadas. **JWTs e tokens de dispositivo não
são revogados por este fluxo**; sua política de revogação permanece separada.

## Privacidade dos logs

O código não inclui exceções do Gmail nem credenciais nos logs de falha. As URLs
de recuperação são ocultadas no handler de arquivo da aplicação. As páginas
usam `no-store` e `Referrer-Policy: strict-origin`, que preserva a origem para CSRF sem expor o caminho do link.

Atualize também as configurações Nginx dos repositórios Docker e `reverse_proxy`:
elas omitem dos access logs as rotas de recuperação que contêm tokens. Valide a
configuração antes de recarregar. Faça a mesma configuração em qualquer outro
proxy, CDN ou coletor de logs da produção que registre URLs completas.

## Desenvolvimento e validação

Com `DEBUG` ativo, o padrão é o backend de console, que mostra os e-mails apenas
nos logs do worker de desenvolvimento. Não use esse backend em produção. Para
validar o Gmail de fato, configure explicitamente o backend Gmail e as
credenciais de uma conta remetente autorizada.

Os testes isolados usam uma caixa de saída em memória e respostas Google
simuladas, sem envio real:

```bash
poetry run pytest tests/security/test_password_recovery.py --ds=myfinance.test_settings
```

Antes de liberar em produção, faça uma solicitação controlada com uma conta de
teste, confira remetente, destinatário, domínio HTTPS e recebimento na caixa de
entrada ou spam e conclua uma recuperação. A autorização e a entrega reais
dependem da configuração Google e não são realizadas pelos testes automatizados.
