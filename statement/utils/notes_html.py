from html import escape
from html.parser import HTMLParser

from django.utils.safestring import mark_safe


class NotesHTMLParser(HTMLParser):
    """Rebuild basic formatting without attributes or executable elements."""

    tags = {'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'p', 'div', 'br', 'ul', 'ol', 'li', 'blockquote'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.suppressed = None

    def handle_starttag(self, tag, attrs):
        if self.suppressed:
            return
        if tag in {'script', 'style'}:
            self.suppressed = tag
        elif tag in self.tags:
            self.parts.append(f'<{tag}>')
            if tag != 'br':
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed:
                self.suppressed = None
            return
        if tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.parts.append(f'</{current}>')
                if current == tag:
                    break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != 'br':
            self.handle_endtag(tag)

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(escape(data))

    def result(self):
        self.close()
        return ''.join(self.parts + [f'</{tag}>' for tag in reversed(self.stack)])


def sanitize_notes(value):
    parser = NotesHTMLParser()
    parser.feed(str(value or ''))
    return parser.result()


def formatted_notes(value):
    return mark_safe(sanitize_notes(value))
