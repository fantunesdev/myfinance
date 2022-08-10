from balanco.models import Movimentacao


def listar_fatura_ano_mes(ano, mes, cartao, usuario):
    return Movimentacao.objects \
        .filter(
                    data_efetivacao__year=ano,
                    data_efetivacao__month=mes,
                    cartao=cartao,
                    usuario=usuario,
                    tela_inicial=True
                ) \
        .order_by('data_lancamento')
