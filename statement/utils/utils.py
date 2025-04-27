class DictToObject:
    """
    Classe utilitária para converter um dicionário em um objeto com atributos dinâmicos.
    """

    def __init__(self, dictionary):
        for key, value in dictionary.items():
            setattr(self, key, value)
