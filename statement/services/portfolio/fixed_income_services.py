from django.db.models import Sum
from decimal import Decimal
from datetime import datetime

from statement.models import FixedIncome

class FixedIncomeService:
    @staticmethod
    def get_investment_progression(user):
        """
        Retorna a progressão dos investimentos para um determinado usuário,
        considerando os vencimentos.
        
        Args:
            user (User): O usuário da requisição
            
        Returns:
            QuerySet: QuerySet com as datas, investimentos diários e montante total
        """
        # Primeiro, obtemos todas as datas de investimento
        investments = FixedIncome.objects.filter(user=user).order_by('investment_date')

        result = []
        running_total = Decimal('0.0')

        # Para cada data, calculamos o montante considerando os vencimentos
        for date in investments.values_list('investment_date', flat=True).distinct().order_by('investment_date'):
            # Investimentos feitos nesta data
            daily_investments = investments.filter(investment_date=date)
            daily_amount = daily_investments.aggregate(total=Sum('principal'))['total'] or 0

            # Investimentos que venceram até esta data (precisam ser subtraídos)
            matured = investments.filter(maturity_date__lte=date).aggregate(total=Sum('principal'))['total'] or Decimal(0)

            # Atualiza o montante total
            running_total += Decimal(daily_amount)
            current_total = running_total - Decimal(matured)

            # Adiciona à lista de resultados
            result.append({
                'date': date.strftime('%Y-%m-%d'),
                'daily_investment': float(daily_amount),
                'total_amount': float(current_total)
            })

        return result

    @staticmethod
    def get_total_amount(user):
        """
        Retorna o montante total atual de investimentos ativos para um usuário.
        
        Args:
            user (User): O usuário da requisição
            
        Returns:
            float: Montante total atual
        """

        current_date = datetime.now().date()

        return FixedIncome.objects.filter(
            user=user,
            investment_date__lte=current_date, # less than or equal
            maturity_date__gt=current_date, # greater than
        ).aggregate(total=Sum('principal'))['total'] or 0
