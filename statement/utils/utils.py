class DictToObject:
    """
    Classe utilitária para converter um dicionário em um objeto com atributos dinâmicos.
    """

    def __init__(self, dictionary):
        self._data = dictionary
        for key, value in dictionary.items():
            setattr(self, key, value)

    def __repr__(self):
        return repr(self._data)

    def __str__(self):
        return str(self._data)
