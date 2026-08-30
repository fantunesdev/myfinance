from django import forms

from statement.forms.base_form import BaseForm
from statement.models import Account, CSVImportConfig, Card


class CSVImportConfigForm(BaseForm):
    MATCHING_FIELD_CHOICES = (
        ('posted_date', 'Data'),
        ('description', 'Descrição'),
        ('original_description', 'Descrição original'),
        ('value', 'Valor'),
        ('account', 'Conta'),
        ('card', 'Cartão'),
        ('card_number', 'Número do cartão'),
        ('category', 'Categoria'),
        ('subcategory', 'Subcategoria'),
        ('type', 'Tipo'),
    )

    matching_fields = forms.MultipleChoiceField(
        choices=MATCHING_FIELD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Campos de batimento',
    )

    class Meta:
        model = CSVImportConfig
        fields = [
            'name',
            'target_model',
            'date_column',
            'description_column',
            'value_column',
            'payment_method',
            'account',
            'card',
            'matching_fields',
        ]
        labels = {
            'name': 'Nome',
            'target_model': 'Importar para',
            'date_column': 'Coluna de data',
            'description_column': 'Coluna de descrição',
            'value_column': 'Coluna de valor',
            'payment_method': 'Meio de pagamento',
            'account': 'Conta',
            'card': 'Cartão',
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['card'].queryset = Card.objects.filter(user=user)

        if self.instance and self.instance.pk:
            self.fields['matching_fields'].initial = self.instance.matching_fields
        elif not self.initial.get('matching_fields'):
            self.fields['matching_fields'].initial = ['posted_date', 'value']

    def clean_matching_fields(self):
        return self.cleaned_data.get('matching_fields') or []
