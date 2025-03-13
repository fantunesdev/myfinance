from typing import Any

from statement.models import Index
from statement.services.index_historical_series_services import IndexHistoricalSeriesServices


class IndexServices(Index):
    """
    Classe de serviços para manipulação e recuperação de objetos do modelo Index.
    Esta classe herda do modelo Index e oferece métodos adicionais para realizar
    operações de consulta no banco de dados.

    A classe inclui métodos para obter todos os registros, buscar por parâmetros
    específicos, além de fornecer uma interface para manipulação de dados do modelo
    Index.

    Métodos:
        __init__(*args: Any, **kwargs: Any) -> None:
            Inicializa uma instância da classe IndexServices, repassando os argumentos
            para a classe pai (Index).

        __str__() -> str:
            Retorna uma string representando o objeto da instância atual.

        all() -> QuerySet:
            Retorna todos os índices financeiros cadastrados no banco de dados.

        get(**kwargs) -> Index:
            Retorna um único objeto Index com base nos parâmetros fornecidos.
            Levanta uma exceção caso nenhum objeto seja encontrado ou caso mais de um
            objeto corresponda aos filtros.

        filter(**kwargs) -> QuerySet:
            Retorna um QuerySet contendo os objetos Index que correspondem aos
            parâmetros fornecidos. Nunca levanta exceção e pode retornar zero ou mais
            objetos.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Inicializa uma instância da classe IndexServices, repassando os argumentos
        fornecidos para a classe pai (Index).

        Args:
            *args (Any): Argumentos posicionais a serem passados para o modelo Index.
            **kwargs (Any): Argumentos nomeados a serem passados para o modelo Index.
        """
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        """
        Retorna a representação em string do objeto IndexServices.

        Returns:
            str: A representação em string do objeto IndexServices.
        """
        return self.__str__()

    @classmethod
    def all(cls):
        """
        Obtém todos os índices financeiros cadastrados no banco de dados.

        Returns:
            QuerySet: Um QuerySet contendo todos os objetos do modelo Index.
        """
        return Index.objects.all()

    @classmethod
    def get(cls, **kwargs):
        """
        Obtém um único índice financeiro com base nos parâmetros fornecidos.

        Args:
            **kwargs: Parâmetros de filtro para realizar a consulta.

        Returns:
            Index: O objeto Index que corresponde aos parâmetros fornecidos.

        Raises:
            Index.DoesNotExist: Se nenhum objeto Index corresponder ao filtro.
            Index.MultipleObjectsReturned: Se mais de um objeto Index corresponder ao filtro.
        """
        return Index.objects.get(**kwargs)

    @classmethod
    def filter(cls, **kwargs):
        """
        Obtém um conjunto de índices financeiros com base nos parâmetros fornecidos.

        Args:
            **kwargs: Parâmetros de filtro para realizar a consulta.

        Returns:
            QuerySet: Um QuerySet contendo os objetos Index que correspondem aos filtros fornecidos.
        """
        return IndexHistoricalSeriesServices.objects.filter(**kwargs)

    def set_series(index_name):
        pass

    def get_series(index_name):
        pass

    # def update_index_historical_series(self, index_name: str, **kwargs):
    #     index = self.get(description=index_name)
    #     index_historical_series = IndexHistoricalSeriesServices(index=index)
    #     t = index_historical_series.first
    #     print(t)

    # def get_historical_series(self, index_name: str):
    #     index = self.get(description=index_name)
    #     historical_index = IndexHistoricalSeriesServices(index=index)
    #     return historical_index.filter(index_id=index.id)
