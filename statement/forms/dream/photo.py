from django import forms


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) and data else [data]
        if len(files) > 10:
            raise forms.ValidationError('Envie até 10 fotos por vez.')
        return [self.clean_image(file) for file in files]

    def clean_image(self, file):
        if file and file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Cada foto deve ter no máximo 10 MB.')
        image = super().clean(file)
        extensions = {
            'JPEG': 'jpg',
            'PNG': 'png',
            'WEBP': 'webp',
            'GIF': 'gif',
        }
        extension = extensions.get(image.image.format)
        if extension is None:
            raise forms.ValidationError('Use fotos em JPG, PNG, WebP ou GIF.')
        image.name = f'photo.{extension}'
        return image


class DreamPhotoForm(forms.Form):
    photos = MultipleImageField(
        label='Selecionar fotos',
        widget=MultipleImageInput(attrs={'accept': 'image/jpeg,image/png,image/webp,image/gif'}),
    )
