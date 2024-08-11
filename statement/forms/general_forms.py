import datetime

from django import forms

from statement.models import Account, Card


class ExclusionForm(forms.Form):
    confirmation = forms.BooleanField(label='', required=True)


class NavigationForm(forms.Form):
    year = forms.ChoiceField(
        label='',
        choices=((y, y) for y in range(2010, datetime.datetime.today().year + 3)),
        widget=forms.Select(attrs={'class': 'navigation-form'}),
    )
    month = forms.ChoiceField(
        label='',
        choices=(
            (1, 'Janeiro'),
            (2, 'Fevereiro'),
            (3, 'Março'),
            (4, 'Abril'),
            (5, 'Maio'),
            (6, 'Junho'),
            (7, 'Julho'),
            (8, 'Agosto'),
            (9, 'Setembro'),
            (10, 'Outubro'),
            (11, 'Novembro'),
            (12, 'Dezembro'),
        ),
        widget=forms.Select(attrs={'class': 'navigation-form'}),
    )


class UploadFileForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.fields['account'] = forms.ModelChoiceField(
            required=False,
            queryset=Account.objects.filter(user=user),
            widget=forms.Select(attrs={'class': 'form-control'}),
        )
        self.fields['card'] = forms.ModelChoiceField(
            required=False,
            queryset=Card.objects.filter(user=user),
            widget=forms.Select(attrs={'class': 'form-control'}),
        )

    file = forms.FileField()
    payment_method = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=(
            (1, 'Cartão de Crédito'),
            (2, 'Conta Corrente'),
        ),
    )
