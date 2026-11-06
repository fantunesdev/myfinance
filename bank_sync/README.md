# Importação e faturas Pluggy

Integração pessoal de leitura. Credenciais ficam em `.env.pluggy` ou no ambiente do servidor; não são enviadas ao navegador.

```bash
python manage.py migrate bank_sync
python manage.py sync_pluggy --username SEU_USUARIO
```

O comando registra dados externos para revisão, sem criar despesas. A consulta pela interface usa o mesmo serviço; nesta versão é síncrona, com bloqueio de consultas concorrentes. Não há cron, worker ou webhook instalado.

## Revisão

Em `/relatorio_financeiro/importar/`, escolha **Importar pela Pluggy**. A tabela segue o padrão das importações por arquivo/notificação: agrupamento por cartão, seleção de linhas e campos editáveis para data, categoria, subcategoria, descrição e valor. O padrão da importação é **Sem fatura definida**; também é possível escolher uma fatura pelo mês de vencimento. **Cadastrar selecionados** confirma somente as linhas escolhidas da página.

O batimento sugere lançamentos do mesmo cartão/moeda com valor correspondente e data da compra/lançamento ou vencimento da fatura. A descrição original e os dados da parcela ajudam na ordenação, sem exigir nomes idênticos. Até três candidatas aparecem diretamente abaixo da compra, com data, valor, descrição e o botão **Conciliar**. Outros candidatos continuam acessíveis em **Outras opções**. A preparação não cria vínculos automaticamente; a conciliação ocorre com o clique do usuário e preserva nomes, categorias, valores e preferências locais. Só ocorrências novas e sem vínculo aparecem na importação; conflitos e outros estados ficam na visão completa.

**Selecionar todas** inclui somente compras sem candidatas, para não cadastrar novamente as prováveis correspondências. Se a coincidência for outra compra, **É uma nova compra** a seleciona para cadastro sem exigir uma confirmação escondida em opções avançadas. Transações já conciliadas deixam de ser sugeridas. Após a migração do histórico, os IDs externos mantêm a idempotência das novas consultas sem depender desse batimento.

Ao conciliar uma parcela, o sistema também vincula as demais ocorrências já recebidas da mesma compra, mesmo em outras faturas. O grupo considera conta, final do cartão, descrição original, data original e total de parcelas; valores das parcelas podem variar em até um centavo. Cada vínculo exige número da parcela, vencimento e valor correspondentes, usando o parcelamento local ou os dados da compra escolhida como referência. Fontes duplicadas ou candidatas ambíguas permanecem pendentes. A tela informa o total conciliado e as parcelas que ainda precisam de revisão. Esse processo não cria parcelas nem altera valores, datas ou categorias existentes.

Quando a fonte ainda não informa o vencimento da fatura, o backend calcula a estimativa pela mesma regra de fechamento e vencimento do cadastro de transações. Usa a data do lançamento da parcela atual, preenche o campo em **Outras opções** e permite editá-lo sem checkbox de confirmação. Quando disponível, o vencimento oficial do banco tem prioridade. A estimativa não associa a compra a uma fatura bancária.

O TC sugere automaticamente os campos da página e as sugestões ficam separadas de `facts`, que conserva os dados bancários. Correções geram feedback para o treinamento existente. Falha do TC mantém a revisão manual disponível e não modifica os dados originais. O TC atual aceita somente `csv`, `notification`, `manual` e `legacy`: o protocolo usa o contexto genérico `legacy` com `source_app=Inter/MeuPluggy`, mantendo `source_type=pluggy` nos lançamentos financeiros.

Em **Conciliação e opções de importação**, é possível vincular um lançamento existente, atualizar a sugestão, ignorar a ocorrência ou solicitar projeções das parcelas restantes. Projeções são estimativas identificadas no extrato e podem ser conciliadas quando a ocorrência real chegar. Pagamentos de fatura, estornos e eventos não reconhecidos não são criados automaticamente como compras.

## Faturas originais

O menu **Faturas originais**, em `/relatorio_financeiro/importar/pluggy/faturas/`, mostra todas as ocorrências recebidas, incluindo importadas, conciliadas e ignoradas. A seleção é por vencimento, com grupos por final de cartão e valores originais. Gastos, estornos/outros créditos e pagamentos de fatura são discriminados; pagamentos não reduzem a soma de gastos do ciclo. Totais são separados por moeda. Projeções locais não entram nessa visão.

**Importar pendências desta fatura** abre a revisão do mesmo período. **Desfazer vínculo** preserva o lançamento local e retorna a ocorrência à revisão. Alterações da fonte são sinalizadas sem sobrescrever escolhas do usuário.

Consultar a API não força atualização no banco. Paginação completa significa todos os registros disponíveis na Pluggy naquela consulta; não garante que o banco disponibilizou todo o histórico.

## Verificação

```bash
.venv/bin/python -m pytest tests/pluggy tests/transaction tests/classifier --ds=myfinance.test_settings -q
node --test tests/js/*.test.mjs
```

No Docker local, o serviço da sessão é `myfinance-dev-app-myfin-1`. As migrations foram aplicadas e os dados externos consultados. A revisão por fatura conciliou sete ocorrências exatas já existentes sem criar despesas. O total da fatura de novembro foi conferido com o app Inter e a chamada real ao TC foi validada.
