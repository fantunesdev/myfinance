import csv

from balanco.entidades.movimentacao import Movimentacao


def ler_csv():
    csv_file = open('financas.csv', 'r')
    movimentacoes = []
    contador = 1
    try:
        leitor = csv.reader(csv_file, delimiter=';')
        next(leitor)
        for i in leitor:
            movimentacao = Movimentacao(
                data=i[1],
                pagamento=i[2],
                conta=i[7],
                cartao=i[6],
                categoria=i[3],
                subcategoria=i[4],
                descricao=i[5],
                valor=float(i[8].replace(',', '.')),
                parcelas=0,
                pagas=0,
                fixa=i[9],
                anual=i[10],
                moeda=1,
                observacao="NULL",
                lembrar=False,
                tipo='entrada',
                efetivado=True,
                tela_inicial=True,
                usuario=1,
            )
            print(f'INSERT INTO balanco_movimentacao values({i[0]},"{movimentacao.data}","{movimentacao.pagamento}","{movimentacao.descricao}",{movimentacao.valor},{movimentacao.parcelas},{movimentacao.pagas},{movimentacao.fixa},{movimentacao.anual},"{movimentacao.observacao}",{movimentacao.lembrar},"{movimentacao.tipo}",{movimentacao.efetivado},{movimentacao.tela_inicial},{movimentacao.cartao},{movimentacao.categoria},{movimentacao.conta},"{movimentacao.moeda}",{movimentacao.subcategoria},{movimentacao.usuario});')
            movimentacoes.append(movimentacao)
    finally:
        csv_file.close()


ler_csv()
