from statement.utils.text import sanitize_utf8mb3


class TestTextUtils:
    def test_sanitize_utf8mb3_removes_supplementary_unicode_characters(self):
        text = 'Compra aprovada 😊 no cartão final 1234'

        assert sanitize_utf8mb3(text) == 'Compra aprovada  no cartão final 1234'

    def test_sanitize_utf8mb3_keeps_bmp_characters(self):
        text = 'Crédito aprovado R$ 10,00 em Açúcar São João'

        assert sanitize_utf8mb3(text) == text

    def test_sanitize_utf8mb3_ignores_non_string_values(self):
        assert sanitize_utf8mb3(None) is None
        assert sanitize_utf8mb3(123) == 123
