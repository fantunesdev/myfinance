# Parcelas de cartão recebidas pela Pluggy

Cada ocorrência recebida já possui o valor de uma parcela. A confirmação associa
as ocorrências da mesma compra ao `Installment` padrão, sem dividir os valores,
renumerar as parcelas ou gerar despesas adicionais. Projeções solicitadas pelo
usuário também ficam no grupo e são conciliadas quando a ocorrência chegar.

O vencimento usa primeiro a fatura oficial. Na ausência dela, usa o mês de
`billForecastDate` e o dia de vencimento do cartão. Uma estimativa informada na
confirmação continua permitida quando não há fatura oficial. Sem previsão, quando
a instituição repete a data original da compra, a posição da parcela desloca o mês.

O agrupamento exige cartão, compra, total, sequência e calendário compatíveis.
Sequências duplicadas não autorizam juntar compras diferentes. Pequenas diferenças
de centavos entre parcelas são preservadas. Uma nova consulta não sobrescreve datas
locais de ocorrências já confirmadas.

Na edição do grupo, descrição e classificação podem ser ajustadas sem recalcular
datas, valores diferentes ou numeração. Datas e cartão são ajustados na parcela
individual; alterar o total de ocorrências importadas não gera parcelas sintéticas.

## Corrigir os registros existentes

Após publicar o código via Git e executar `mfupdate`, faça backup do banco e simule:

```sh
docker exec app-myfin python manage.py reconcile_pluggy_installments \
  --user 1 --transactions 5272 5273 5246 5247 5248
```

O relatório mostra antes/depois; a simulação desfaz todas as alterações. Para
aplicar o agrupamento, acrescente `--apply`. As datas já corrigidas dessas cinco
parcelas serão preservadas. O total negativo da primeira parcela Vital Care será
normalizado para 2, sem alterar seu valor.

`--source-dates` também substitui os vencimentos pelos dados bancários. Use somente
quando essa substituição for desejada; não é necessário para os cinco registros
acima, cujas datas em produção já foram conferidas.
