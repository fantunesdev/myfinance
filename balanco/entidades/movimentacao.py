class Movimentacao():
    def __init__(self, data, pagamento, conta, cartao, categoria, subcategoria, descricao, valor, parcelas, pagas,
                 fixa, anual, moeda, observacao, lembrar, tipo, efetivado, tela_inicial, usuario):
        self.data = data
        self.pagamento = pagamento
        self.conta = conta
        self.cartao = cartao
        self.categoria = categoria
        self.subcategoria = subcategoria
        self.descricao = descricao
        self.valor = valor
        self.parcelas = parcelas
        self.pagas = pagas
        self.fixa = fixa
        self.anual = anual
        self.moeda = moeda
        self.observacao = observacao
        self.lembrar = lembrar
        self.tipo = tipo
        self.efetivado = efetivado
        self.tela_inicial = tela_inicial
        self.usuario = usuario
