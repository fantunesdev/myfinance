"""Environment parsing without loading secrets or Django settings."""
import os


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    if value.strip().lower() in ('true', '1', 'yes', 'on'):
        return True
    if value.strip().lower() in ('false', '0', 'no', 'off', ''):
        return False
    raise ValueError(f'{name} deve ser um booleano válido.')
