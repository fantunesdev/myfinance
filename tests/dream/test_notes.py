import pytest
from django.template import Context, Template

from statement.forms.dream.dream import DreamForm
from statement.utils.notes_html import sanitize_notes


@pytest.mark.parametrize('html', [
    '<b>Negrito</b> e <i>itálico</i>',
    '<u>Sublinhado</u><br><ul><li>Primeiro</li><li>Segundo</li></ul>',
    '<p>Parágrafo</p><ol><li>Item</li></ol>',
    'Texto simples\nOutra linha &amp; mais texto',
])
def test_notes_preserve_basic_formatting(html):
    assert sanitize_notes(html) == html
    result = Template('{% load custom_filters %}{{ notes|formatted_notes }}').render(Context({'notes': html}))
    assert result == html


@pytest.mark.parametrize('html', [
    '<script>alert(1)</script><b onclick="alert(1)">Texto</b>',
    '<img src=x onerror=alert(1)><b>Texto</b>',
    '<svg><foreignObject><b onmouseover=alert(1)>Texto</b></foreignObject></svg>',
    '<style>body {display:none}</style><b style="position:fixed">Texto</b>',
    '<a href="javascript:alert(1)"><b>Texto</b></a>',
    '<iframe srcdoc="<script>alert(1)</script>"></iframe><b>Texto</b>',
])
def test_notes_rebuild_only_allowed_tags_without_attributes(html):
    assert sanitize_notes(html) == '<b>Texto</b>'


def test_notes_balance_tags_and_escape_text():
    assert sanitize_notes('</div><b>Texto') == '<b>Texto</b>'
    assert sanitize_notes('1 < 2 & 3 > 2') == '1 &lt; 2 &amp; 3 &gt; 2'
    assert sanitize_notes('&lt;script&gt;alert(1)&lt;/script&gt;') == '&lt;script&gt;alert(1)&lt;/script&gt;'


def test_dream_form_cleans_notes_and_renders_editor():
    form = DreamForm(data={'notes': '<b onclick="alert(1)">Texto</b><script>alert(1)</script>'})
    form.is_valid()
    assert form.cleaned_data['notes'] == '<b>Texto</b>'
    html = str(DreamForm(initial={'notes': '<img src=x onerror=alert(1)><b>Texto</b>'})['notes'])
    assert 'data-command="bold"' in html
    assert '<b>Texto</b></div>' in html
    assert '<img ' not in html
