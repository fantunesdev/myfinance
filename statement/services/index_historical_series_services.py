import requests

from collections import defaultdict
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any

from statement.models import IndexHistoricalSeries

class IndexHistoricalSeriesServices(IndexHistoricalSeries):
    """
    Classe de serviços para séries históricas de índices.
    """
    
    def __init__(self, index: object, *args: Any, **kwargs: Any) -> None:
        """
        Inicializa uma instância da classe IndexHistoricalSeriesServices, 
        repassando os argumentos fornecidos para a classe pai (IndexHistoricalSeries).
        
        Args:
            index_name (str): Nome do índice.
            *args (Any): Argumentos posicionais a serem passados para o modelo Index.
            **kwargs (Any): Argumentos nomeados a serem passados para o modelo Index.
        
        Raises:
            ValueError: Se 'index_name' não for fornecido.
        """
        # Verifica se o parâmetro 'index_name' foi fornecido
        if not index:
            raise ValueError("O parâmetro 'index' deve ser fornecido ao instanciar a classe.")

        # Chama o construtor da classe pai
        super().__init__(*args, **kwargs)

        # Armazena o nome do índice
        self.index = index

        # Busca o primeiro e último registros com base no nome do índice
        self.first = IndexHistoricalSeries.objects.filter(index=self.index.id).first()
        self.last = IndexHistoricalSeries.objects.filter(index=self.index.id).last()

    def __eq__(self, value: object) -> bool:
        return self.date == value.date

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
    
    def fetch_index(self, **kwargs) -> Any:
        """
        Busca a série histórica de um índice financeiro entre datas específicas.

        Args:
            **kwargs: Parâmetros opcionais, como data inicial e final.

        Raises:
            ValueError: Se o índice não estiver disponível.
            ConnectionAbortedError: Se a conexão falhar ao tentar obter os dados da API.

        Returns:
            Any: Dados JSON da série histórica do índice.
        """
        today = date.today()
        available_indices = {
            'selic': {
                'id': 432,
                'first_date': '01/03/1986',
                'last_date': today.strftime('%d/%m/%Y'),
            },
            'cdi': {
                'id': 13,
                'first_date': '02/01/1995',
                'last_date': today.strftime('%d/%m/%Y'),
            },
        }

        # Verifica se o índice está disponível
        index_name = self.index.description.lower()
        if index_name not in available_indices:
            raise ValueError(f"Índice '{index_name}' não disponível.")  # Erro para índice não encontrado

        # Instanciar o SimpleNamespace
        selected_index = SimpleNamespace(**available_indices[index_name])
        
        initial_date = kwargs.get('initial_date', None)
        final_date = kwargs.get('final_date', None)

        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{selected_index.id}/dados'

        if not initial_date:
            initial_date = selected_index.first_date

        if not final_date:
            final_date = selected_index.last_date

        params = {
            'formato': 'json',
            'dataInicial': initial_date,
            'dataFinal': final_date,
        }

        # Faz a requisição para a API
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()

        raise ConnectionAbortedError(f"Erro ao tentar se conectar à API: {str(requests.RequestException)}")
    
    def update_index_historical_series(self, **kwargs):
        index_series = self.fetch_index()
            
        # Processar os dados para obter valores mensais
        monthly_data = defaultdict(list)

        for record in historical_series:
            date_str = record['data']
            value = float(record['valor'])
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            month_key = (date_obj.year, date_obj.month)  # Usar ano e mês como chave

            monthly_data[month_key].append(value)

        # Calcular o valor mensal (pode ser a média ou o último valor)
        monthly_averages = {
            f"{year}-{month:02d}-01": sum(values) / len(values)  # Média dos valores
            for (year, month), values in monthly_data.items()
        }

        # Exibir os resultados
        for date, average in monthly_averages.items():
            new_rate = IndexHistoricalSeries.objects.create(
                date=date,
                rate=average,
                index=self.index
            )
            new_rate.save()
