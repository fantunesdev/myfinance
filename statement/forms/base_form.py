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
            is_not_checkbox = not isinstance(field.widget, forms.CheckboxInput)
            is_not_file = not isinstance(field.widget, forms.FileInput)
            is_not_image = not isinstance(field.widget, forms.ImageField)
            if is_not_checkbox and is_not_file and is_not_image:
                field.widget.attrs.setdefault('class', 'form-control')
