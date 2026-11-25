import logging
import re


class RecoveryURLFilter(logging.Filter):
    """Avoid persisting reset credentials in application request logs."""

    pattern = re.compile(r'(/usuarios/senha/recuperar/)[^/\s?]+/[^/\s?]+/')

    def filter(self, record):
        message = record.getMessage()
        record.msg = self.pattern.sub(r'\1[redacted]/', message)
        record.msg = re.sub(r'(/usuarios/seguranca/email/confirmar/)[^/\s?]+/', r'\1[redacted]/', record.msg)
        record.args = ()
        return True
