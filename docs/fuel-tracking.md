# Acompanhamento de combustível

Ative o acompanhamento e selecione a subcategoria em Perfil → Combustível.
Ao selecionar essa subcategoria no lançamento, informe o valor total pago, já com
desconto, e os litros ou o preço efetivo por litro. Ao editar os litros, o preço
é calculado; ao editar o preço, os litros são calculados. Alterações no valor
pago respeitam o último desses dois campos que você editou. O preço informado
fica preservado na edição, sem depender do arredondamento dos litros calculados.
As observações continuam disponíveis para comentários livres.

A distância desde o abastecimento anterior é opcional e produz uma prévia de
consumo e custo por km. A quilometragem total do veículo também é opcional.
Informe se completou o tanque; abastecimentos parciais podem ser registrados
normalmente.

O consumo pelo hodômetro usa dois abastecimentos com tanque cheio e hodômetro:
a diferença entre as leituras é dividida pelos litros abastecidos depois do
registro inicial, incluindo o final. Todos os abastecimentos intermediários
precisam ter os litros registrados, mas não precisam ter hodômetro. Os litros
do registro inicial ficam fora da conta.

Se esquecer um abastecimento, marque a interrupção no próximo registro. O próximo
tanque cheio com hodômetro inicia uma nova referência. Excluir um abastecimento
também marca uma interrupção no registro seguinte. Registre abastecimentos do
mesmo dia na ordem em que ocorreram.

Em Dashboards → Gastos por categoria, clique na categoria da subcategoria
configurada (por exemplo, Transporte) ou na própria subcategoria. O bloco
Combustível mostra o histórico completo do veículo, independentemente do ano
selecionado no gráfico financeiro. Clique no consumo para ver os períodos,
litros e distâncias dos períodos válidos usados no cálculo.

A distância informada fica restrita ao consumo e ao custo individuais do
abastecimento, apresentados no formulário e nos detalhes do lançamento. A média
histórica usa exclusivamente as diferenças de hodômetro e os litros dos
intervalos completos. Um registro isolado com distância informada não inicia
essa média: é necessário ter duas referências de tanque cheio com hodômetro.

Um histórico contínuo pelo hodômetro cresce como um único período. Interrupções separam os
períodos; a média geral é a soma das distâncias dividida pela soma dos litros,
sem sobrepor períodos ou calcular uma média simples dos consumos. Os valores
monetários usam esses mesmos períodos; intervalos com moedas diferentes não
produzem médias monetárias combinadas.

Cada abastecimento está ligado a um lançamento. Em compras parceladas, apenas
o lançamento inicial possui os dados físicos e o total do abastecimento fica
preservado. Ao editar esse lançamento, há um campo específico para corrigir o
total pago, sem confundi-lo com o valor de uma parcela.

As migrations importam os valores reconhecidos nos blocos antigos de observação,
preservando o texto original. Distância zero é tratada como não informada. Tanque
cheio permanece não informado: só corrija registros antigos se souber como foram
feitos. Blocos ambíguos permanecem no texto para revisão manual.
