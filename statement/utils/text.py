import re


def sanitize_utf8mb3(text: str):
    if not isinstance(text, str):
        return text
    return re.sub(r'[\U00010000-\U0010FFFF]', '', text)
