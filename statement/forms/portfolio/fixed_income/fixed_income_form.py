from django import forms

from statement.models import FixedIncome


class FixedIncomeForm(forms.ModelForm):
    class Meta:
        model = FixedIncome
        fields = ['account', 'principal', 'security', 'investment_date', 'maturity_date', 'index', 'contractual_rate']
