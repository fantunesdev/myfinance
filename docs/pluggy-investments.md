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
