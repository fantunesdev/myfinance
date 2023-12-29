from django import forms


class ExclusionForm(forms.Form):
    confirmation = forms.BooleanField(label='', required=True)



class NavigationForm(forms.Form):
    year = forms.ChoiceField(
        label='',
        choices=(
            (y, y) for y in range (2015, 2025)
        ),
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
