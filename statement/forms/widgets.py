from django import forms

from statement.utils.notes_html import formatted_notes


class SimpleRichTextWidget(forms.Textarea):
    template_name = 'components/simple_rich_text.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['formatted_value'] = formatted_notes(value)
        return context

    class Media:
        css = {'all': ('css/simple-rich-text.css',)}
        js = ('js/components/simple-rich-text.js',)
