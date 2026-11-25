# Identidade e autenticação em duas etapas

O MyFinance distingue o e-mail de recuperação, as contas Google conectadas e a
conta remetente que envia mensagens. Esses endereços podem ser diferentes.
A segurança da conta fica em **Perfil → Gerenciar e-mail e autenticador**.

## E-mail de recuperação e conta Google

O perfil mostra o e-mail de recuperação e seu estado de confirmação. A conta
Google continua vinculada pelo identificador estável do provedor; conectar ou
confirmar o Google não troca automaticamente o endereço cadastrado.

O endereço de cada conta Google é atualizado após uma autenticação Google bem
sucedida. Vínculos antigos sem esse dado continuam funcionando; confirme a conta
Google novamente para identificar o endereço no perfil. Somente e-mail e estado
de verificação do provedor são guardados como metadados, sem seus tokens.

Para trocar o e-mail de recuperação:

1. Confirme sua identidade por senha ou Google; com 2FA ativo, confirme também o
   autenticador ou um código de recuperação.
2. Informe o novo endereço, ou clique em **Usar este e-mail do Google**.
3. Aguarde a mensagem no novo endereço e abra o link na mesma conta MyFinance.
4. Confirme a alteração na página. O link dura 24 horas e exige sessão recente.

Até a confirmação, o endereço antigo continua sendo o de recuperação. A ação
não altera o vínculo Google. Cancelar ou emitir outra solicitação invalida os
links anteriores. Um endereço pertencente a outra conta não pode ser usado,
inclusive quando a diferença for apenas de letras maiúsculas e minúsculas.

Ao confirmar uma mudança, os links antigos de recuperação deixam de valer e os
outros acessos humanos são revogados. O endereço anterior recebe aviso se já
estava confirmado; não enviamos essa notificação a endereços antigos não
verificados. Confirmar o endereço atual também está disponível, sem trocar a
conta. Contas existentes começam com confirmação pendente, mas mantêm o acesso
atual e a recuperação de senha durante essa transição.

A edição comum do perfil não altera mais o e-mail diretamente. Nenhuma conta é
mesclada automaticamente por coincidência de endereço.

## Ativar ou substituir o autenticador

Confirme o e-mail de recuperação primeiro. Em seguida, confirme sua identidade e
abra **Configurar autenticador**. Gere o QR Code, escaneie no aplicativo
autenticador ou digite a chave manualmente e confirme um código de seis dígitos.

A configuração pendente expira em dez minutos. O 2FA só é ativado após validar o
código. Ao substituir um autenticador, o anterior continua válido até a
confirmação do novo. O QR Code é gerado localmente, sem enviar o segredo a
serviços externos. O código muda a cada 30 segundos e aceita tolerância de um
intervalo; mantenha o relógio do servidor e do celular sincronizados.

Após ativar ou substituir, são exibidos dez códigos de recuperação, somente
naquela resposta. Guarde-os fora do celular. Cada código é de uso único; o banco
guarda apenas hashes SHA-256 de códigos aleatórios de 128 bits. Gerar um novo
conjunto invalida o anterior. Um código consumido para confirmar uma ação de
segurança também deixa de estar disponível para login.

O segredo TOTP é criptografado com Fernet. A verificação usa as primitivas TOTP
do `django-otp`, transações e bloqueio de dispositivo. O último intervalo aceito
é registrado para impedir reutilização simultânea. Erros aplicam espera
progressiva de até cinco minutos; há também limite de 30 tentativas por IP a
cada cinco minutos no Redis. Falha no cache ou na chave não libera acesso.

## Login e confirmação de identidade

Contas sem 2FA continuam usando senha ou Google. Contas com 2FA seguem:

```text
Senha ou Google → Código do autenticador ou de recuperação → Sessão completa
```

O desafio intermediário dura cinco minutos e não cria uma sessão autenticada.
Mudanças de senha ou versão de segurança invalidam desafios pendentes. A sessão
é renovada após a validação, incluindo o identificador do logout por inatividade.
O Google não dispensa o segundo fator local do MyFinance.

Alterações sensíveis exigem confirmação recente, de até cinco minutos. Com
senha local, confirme senha e segundo fator; com conta exclusivamente Google,
confirme o segundo fator, se ativo, e a conta Google. O mesmo código TOTP não
pode ser reutilizado em duas ações: aguarde o próximo código ou use outro código
de recuperação. Uma ação enviada antes da confirmação recente deve ser revisada
e reenviada após confirmar a identidade.

Desativar o 2FA exige uma sessão recente e um código válido. A recuperação de
senha por e-mail mantém o 2FA e seus códigos; ela não substitui o segundo fator.
Não há dispensa por navegador lembrado nesta versão.

## API e automações

- `/api/token/` continua recebendo `username` e `password`. Para usuários com
  2FA, inclua também `otp`, com um código TOTP ou de recuperação. Sem código
  válido, nenhum JWT é devolvido.
- Os JWTs recebem versão de segurança e indicação do método de autenticação.
  O refresh é rejeitado quando a versão deixa de ser atual. JWTs antigos de
  usuários que ainda não alteraram a versão de segurança continuam compatíveis.
- A API por sessão e o Django Admin exigem uma sessão com o segundo fator
  concluído. O Admin encaminha o login para o fluxo central.
- WebSockets verificam a sessão na conexão e antes de enviar dados; mudanças de
  segurança também solicitam o encerramento das conexões existentes.
- O grant OAuth2 por senha é bloqueado para usuários com 2FA. Autorização por
  navegador usa a sessão completa. Grants e tokens OAuth2 anteriores do usuário
  são revogados nas alterações de segurança.
- Tokens de dispositivo já cadastrados continuam disponíveis para automações;
  sua visualização e gerenciamento exigem confirmação recente. Serviços internos
  usam JWTs delegados assinados no servidor e vinculados à versão de segurança.

Ativar, substituir, desativar, regenerar códigos ou mudar o e-mail confirmado
invalida outras sessões e JWTs anteriores. A sessão que concluiu a alteração
permanece válida. As ações ficam em `SecurityAuditEvent`, sem códigos ou segredos.

## Recuperação administrativa

Se o usuário perder o autenticador e todos os códigos, o administrador precisa
verificar sua identidade por um procedimento externo confiável. Só então, no
ambiente autorizado de administração do servidor, execute:

```bash
poetry run python manage.py reset_two_factor NOME_DO_USUARIO \
  --reason "Identidade verificada pelo procedimento administrativo"
```

O comando desativa o segundo fator, remove o dispositivo e os códigos, revoga
os acessos humanos anteriores e registra a justificativa. Ele não muda senha,
e-mail ou contas Google. Não existe endpoint público de remoção administrativa,
e uma mensagem recebida por e-mail, sozinha, não deve autorizar a remoção.

## Publicação e chave de criptografia

Atualize os repositórios MyFinance e Docker e reconstrua a imagem para instalar
`django-otp` e `segno`. A migração `login.0009` adiciona os campos de identidade e
as tabelas de autenticador, códigos, auditoria e mensagens de confirmação. O
worker existente `password-reset-email` passa a processar também essas mensagens.

Antes de permitir ativação de autenticadores em produção, gere uma chave
exclusiva para esse ambiente, em uma máquina administrativa confiável:

```bash
mkdir -p ~/.config/myfinance
umask 077
poetry run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
  > ~/.config/myfinance/2fa-production-key
```

Abra o arquivo privado no editor e configure seu conteúdo no `.env` do Compose:

```dotenv
TWO_FACTOR_ENCRYPTION_KEY=
```

O Compose encaminha a variável aos serviços. Não versione nem compartilhe a
chave; mantenha backup protegido junto da política de backup do banco.
**Não gere uma chave diferente em cada deploy.** Um banco com autenticadores
cadastrados precisa da chave correspondente aos dados criptografados. Perder ou
substituir a chave impede a validação desses autenticadores; não existe fallback
que dispense o segundo fator. O desenvolvimento local já recebeu sua própria
chave no `.env`, sem ativar 2FA em nenhuma conta existente.

As mensagens usam a configuração Gmail já documentada em
[Recuperação de senha](recuperacao-senha.md). Atualize as configurações Nginx dos
repositórios Docker e `reverse_proxy` para omitir dos access logs os links de
confirmação de e-mail. As páginas de segurança usam `no-store` e
`Referrer-Policy: strict-origin`, compatível com os formulários CSRF.

## Validação

```bash
poetry run pytest tests/security/test_identity_two_factor.py --ds=myfinance.test_settings
```

Os testes usam banco descartável, chaves de teste e e-mails em memória. A
validação em navegador real usa dados sintéticos e não envia mensagens Gmail.
A chave de produção e o procedimento de confirmação de identidade administrativa
precisam ser mantidos pelo operador.
