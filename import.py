import csv

from balanco.entidades.movimentacao import Movimentacao


def ler_csv():
    csv_file = open('financas.csv', 'r')
    movimentacoes = []
    try:
        leitor = csv.reader(csv_file, delimiter=';')
        next(leitor)
        for i in leitor:
            movimentacao = Movimentacao(
                data=i[1],
                pagamento=i[2],
                conta=i[8],
                cartao=i[7],
                categoria=i[3],
                subcategoria=i[4],
                descricao=i[5],
                valor=i[6],
                parcelas=0,
                pagas=0,
                fixa=i[9],
                anual=i[10],
                moeda='BRL',
                observacao=None,
                lembrar=None,
                tipo='saida',
                efetivado=True,
                tela_inicial=True,
                usuario=1,
            )
            movimentacoes.append(movimentacao)
        print(movimentacoes)
    finally:
        csv_file.close()


ler_csv()
