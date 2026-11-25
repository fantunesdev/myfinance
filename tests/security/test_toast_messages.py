import pytest
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


@pytest.mark.parametrize('level,variant,role', [(20, 'info', 'status'), (25, 'success', 'status'), (30, 'warning', 'status'), (40, 'error', 'alert')])
def test_feedback_has_accessible_role_and_correct_color_variant(level, variant, role):
    html = render_to_string('_frames/_toasts.html', {'messages': [Message(level, 'Mensagem de retorno')]})
    assert f'data-toast-level="{variant}"' in html
    assert f'role="{role}"' in html
    assert 'aria-label="Fechar notificação"' in html
    assert html.count('Mensagem de retorno') == 1


def test_feedback_always_displays_html_as_text():
    html = render_to_string('_frames/_toasts.html', {'messages': [Message(40, mark_safe('<img src=x onerror=alert(1)>'))]})
    assert '<img' not in html
    assert '&lt;img src=x onerror=alert(1)&gt;' in html
