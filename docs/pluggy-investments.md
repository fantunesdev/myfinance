# Investimentos pela Pluggy

O botão **Atualizar pela Pluggy** atualiza posições, quantidades e avaliações.
Variação de saldo não gera aporte, resgate ou lucro. A consulta precisa terminar
completa, sem mudança da referência da conexão. Posições ausentes não são zeradas.
A proteção contra caixa pendente de alocação continua ativa.

Em **Conciliar movimentações**, **Consultar movimentações** enfileira uma coleta
persistida de eventos dos títulos e das liquidações das contas bancárias. A coleta
não altera lançamentos financeiros. A cobertura depende do histórico efetivamente
fornecido pela instituição; ausência de eventos não comprova ausência de operações.

## Página de conciliação

A aba **A revisar** é a visão inicial e reúne apenas eventos novos, históricos
pendentes e alterações na fonte. Quando tudo foi resolvido, ela mostra zero
pendências e um acesso ao histórico. Os totais das abas consideram todos os
eventos do usuário, independentemente da página exibida.

A aba **Histórico** contém eventos registrados, vinculados ou ignorados. A lista
é ordenada por data e paginada, com detalhes recolhidos e sem formulários de
reaplicação. Ao abrir um evento, são mostrados os lançamentos e comprovantes
vinculados. A classificação confirmada prevalece sobre o rótulo original da
instituição; os dados originais continuam disponíveis nos detalhes. Operações
agrupadas identificam que seus comprovantes pertencem ao conjunto.

Nas pendências, os campos acompanham a ação escolhida. Eventos anteriores à
data-base oferecem vínculo ou descarte justificado; conflitos oferecem a
preservação justificada dos registros locais. Compras e transferências podem ser
agrupadas quando necessário. A consulta em segundo plano preserva o texto da
revisão aberta e avisa quando a lista tiver informações novas.

## Processamento

Além do servidor web, mantenha um processo com o mesmo código, configurações,
acesso ao banco e credenciais da aplicação:

```sh
python manage.py migrate --noinput
python manage.py process_investment_history
```

`--once` processa no máximo uma tarefa e termina. A conexão é reservada durante a
coleta para evitar competição com outras consultas. Uma execução interrompida é
marcada como falha quando uma nova coleta é solicitada após a reserva expirar.
Nenhuma opção do trabalhador aplica proventos automaticamente.

## Conciliação

Cada confirmação exige evidência escrita e uma versão atual do evento. As
liquidações usadas precisam estar efetivadas, em BRL, próximas da data do evento,
com direção e valor líquido correspondentes. Uma liquidação não pode financiar
duas operações independentes.

- **Vincular ao histórico** associa o evento aos lançamentos existentes e não
  muda valores. A seleção exige conferência documental pelo operador.
- **Aplicar operação** registra compra, venda, provento, tributo ou amortização.
  Compras e tributos exigem distribuição explícita entre créditos de caixa.
  Vendas exigem quantidade e principal/custo comprovados; sem isso ficam pendentes.
- Compras da mesma liquidação podem ser agrupadas, incluindo custo compartilhado
  comprovado na nota. Duas pernas de transferência de custódia do mesmo ativo
  podem ser agrupadas com custo comprovado, sem criar aporte externo ou lucro.
- Proventos pagos geram resultado no ativo e crédito líquido no caixa, sem
  aumentar a posição do título. Tributos são registrados separadamente.
- **Ignorar com motivo** preserva a fonte sem criar lançamentos.

A aplicação é atômica, protege os lançamentos conciliados contra edição isolada e
preserva uma posição oficial posterior que já contenha o evento. Repetir a mesma
confirmação não duplica seus lançamentos.

## Histórico e revisões

A aba **Extrato bancário** mostra comprovantes bancários BRL efetivados,
sem vínculo com uma conciliação: resgates (`Resgate - `), aplicações
(`Aplicação - `), compras de criptomoedas (`Compra - Criptomoedas`) e liquidações
B3 (`Débito B3 - `). São descrições reconhecidas, não uma classificação universal
de todos os bancos. A lista tem paginação própria e não aumenta o contador de
eventos de investimento a revisar. Um comprovante pode chegar sem evento no
histórico de investimentos e também pode corresponder a um lançamento local já
existente. Sua exibição não cria lançamentos nem modifica saldos.

Nessa aba, é possível vincular um comprovante a um lançamento próprio do mesmo
valor e sentido, até sete dias antes/depois, ou confirmar com justificativa que
o valor já está incluído no histórico. Nenhuma dessas ações cria movimentos
financeiros. Quando uma compra de criptomoedas tem um resgate de origem
documentado, a opção **Registrar resgate e compra** registra o fluxo inteiro.
O usuário informa somente a moeda e a quantidade que o extrato não trouxe.
O aplicativo não fabrica eventos da Pluggy para preencher essa ausência.

As conferências ficam em **Extrato bancário → Conferidos**, com justificativa
e lançamentos vinculados. Cada revisão do comprovante exige nova conferência,
preservando a anterior. Lançamentos vinculados não podem ser editados ou
excluídos isoladamente. Um lançamento não pode explicar dois comprovantes
independentes da mesma versão da fonte.

Após uma coleta completa bem-sucedida, o trabalhador tenta vincular registros
existentes e importar operações completas automaticamente. O botão **Processar
dados recebidos** faz a mesma verificação com os dados já coletados, sem consultar
a Pluggy. Atualizar as posições também agenda o processamento do histórico.
Os vínculos criados
pela aplicação financeira de um evento já são guardados atomicamente e não são
refeitos. A identificação usa o ID externo estável do evento, e não só seu valor.

A recuperação de vínculos de compra/resgate exige correspondência única entre
título mapeado (ou origem consolidada documentada), data exata, valor líquido,
quantidade quando disponível e comprovante bancário do mesmo tipo de operação.
O lançamento deve ter um par de caixa do mesmo valor/data. Comprovantes isolados
exigem também banco, família do ativo, par de caixa e ausência de eventos que
possam disputar o mesmo registro. Duplicidades, revisões, Pix do mesmo valor,
taxas sem correspondência e fontes incompletas continuam para revisão. Não são
criados aportes, resgates ou rendimentos na etapa que apenas recupera vínculos.

A etapa seguinte registra eventos novos posteriores à abertura auditada:
compras com quantidade e caixa de origem inequívocos, resgates com custo e
quantidade conhecidos e proventos com valores bruto/líquido e crédito bancário.
Tudo fica vinculado ao ID externo original na mesma transação financeira.
Novos títulos de renda fixa e ações com ticker explícito podem ser cadastrados
a partir de compra, posição oficial, data de aquisição e instituição identificadas.
Sem origem de dinheiro,
com dados conflitantes, duplicidades ou histórico de custo incompleto, a operação
permanece pendente com o motivo. Essa etapa não infere aportes externos a partir
de diferenças de saldo.

Para compra de cripto recebida só no extrato, o aplicativo exige débito e resgate
únicos, da mesma conta, data e valor. Se o resgate já está registrado, consome
exatamente o crédito de caixa existente. Se a instituição só informou o encerramento
do título, exige aquisição conciliada, resgates anteriores documentados e posição
anterior confirmando a quantidade remanescente. Eventuais correções de registros
consolidados ficam em uma auditoria com valores anteriores/posteriores e provas;
os fatos e snapshots originais da instituição são preservados.

O resgate, o caixa e a compra são registrados atomicamente. O destino fica na
custódia do banco, separado de Bitcoin em outras exchanges. Sem cotação fornecida,
o valor inicial é o custo pago; não é apresentado como uma cotação de mercado.
Uma repetição não cria nova compra. Se o evento oficial chegar depois, ele adota
os registros existentes pela mesma quantidade, liquidação, título e valor.
Revisões da fonte preservam os movimentos e abrem conflito; manter os registros
exige confirmação com justificativa. Compras e resgates nunca são apagados ou
reaplicados para acompanhar uma revisão silenciosamente.

Quando todos os títulos BRL mapeados da conexão têm abertura auditada,
comprovantes até a menor dessas datas ficam em **Anteriores à abertura**.
Essa separação é temporal: não afirma uma correspondência individual e não
marca os comprovantes como conciliados. Eles continuam disponíveis para consulta.
Novas operações sem registro permanecem em **A conferir**. Revisões e decisões
manuais são preservadas; conflitos não são resolvidos automaticamente.

Para uma prévia operacional: `python manage.py reconcile_investment_history
--connection ID`. Acrescente `--apply` para gravar somente os vínculos. O comando
exige que a última coleta da conexão tenha sido concluída com sucesso e que não
haja execução em andamento; não solicita uma atualização externa.

Resgates históricos também podem ser vinculados ao investimento consolidado
usado na abertura auditada do título individual, quando existir o par de
transferências do mesmo valor, na data-base, entre títulos de renda fixa do
mesmo banco. Exige valor líquido idêntico e data próxima; o vínculo apenas
documenta a correspondência e não transfere dinheiro entre esses títulos.

A abertura auditada de novembro de 2026 tem uma data-base. Eventos anteriores
podem ser vinculados ao existente; não podem criar lançamentos isolados sobre a
abertura, pois isso duplicaria patrimônio. Substituir essa abertura por uma
reconstrução histórica completa ainda exige outra operação auditada. O coletor
não importa as planilhas e CSVs históricos.

Revisões da fonte preservam versões anteriores e marcam toda a operação composta
como conflito. Os lançamentos locais permanecem intactos. **Manter conciliação
local após conflito** exige justificativa e aceita expressamente a divergência.
Substituir automaticamente uma operação já aplicada pela versão revisada não é
suportado; exige reconstrução e conferência de suas dependências.

O painel identifica resultado confirmado por conciliação e pendências. Resultado
legado e gráficos continuam incluindo valores ainda não conferidos. O valor
confirmado é parcial, não o rendimento total certificado da carteira.

Crédito recebido não prova que o dinheiro segue disponível hoje. Saídas para
consumo, transferências e reinvestimentos posteriores precisam ser conciliados
antes de considerar o saldo reconstruído. Por isso, a coleta não confirma nem
aplica proventos por conta própria. Eventos ambíguos, câmbio, fator de preço não
unitário e transferências entre ativos distintos ficam para revisão.

## Instalação atual

Em produção, o processo da fila roda no contêiner
`myfinance-investment-history`, com reinício automático (`unless-stopped`), na
mesma rede e com a configuração da aplicação. Ele lê o código persistente em
`/docker/myfinance/myfinance` e grava logs no diretório compartilhado da aplicação.
Após publicar mudanças do trabalhador, reinicie também esse contêiner. Ao
reconstruir a imagem ou mudar variáveis do aplicativo, recrie o trabalhador com a
mesma imagem e configuração; reiniciar não altera a imagem nem suas variáveis.
As credenciais não são mantidas em arquivos temporários após sua criação.
