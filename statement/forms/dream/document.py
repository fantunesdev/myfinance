from pathlib import Path

from django import forms


class MultipleDocumentInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePDFField(forms.FileField):
    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) and data else [data]
        if len(files) > 10:
            raise forms.ValidationError('Envie até 10 documentos por vez.')
        return [self.clean_pdf(file) for file in files]

    def clean_pdf(self, file):
        file = super().clean(file)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Cada documento deve ter no máximo 10 MB.')
        if Path(file.name).suffix.lower() != '.pdf':
            raise forms.ValidationError('Envie apenas documentos em PDF.')
        try:
            header = file.read(8)
        finally:
            file.seek(0)
        if not header.startswith(b'%PDF-'):
            raise forms.ValidationError('O arquivo enviado não é um PDF válido.')
        return file


class DreamDocumentForm(forms.Form):
    documents = MultiplePDFField(
        label='Escolher PDFs',
        widget=MultipleDocumentInput(attrs={'accept': '.pdf,application/pdf'}),
    )
