from django import forms

class BaseForm(forms.ModelForm):
    """
    Formulário base para reutilização de lógica comum entre os forms.
    """
    def __init__(self, *args, **kwargs):
        """
        Reescreve o inicializador da classe para adicionar a classe form-control no input
        """
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')
