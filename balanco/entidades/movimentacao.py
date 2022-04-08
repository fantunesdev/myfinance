class Movimentacao():
    def __init__(self, data_lancamento, data_efetivacao, conta, cartao, categoria, subcategoria, descricao, valor,
                 numero_parcelas, pagas, fixa, anual, moeda, observacao, lembrar, tipo, efetivado, tela_inicial,
                 usuario):
        self.data_lancamento = data_lancamento
        self.data_efetivacao = data_efetivacao
        self.conta = conta
        self.cartao = cartao
        self.categoria = categoria
        self.subcategoria = subcategoria
        self.descricao = descricao
        self.valor = valor
        self.numero_parcelas = numero_parcelas
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
