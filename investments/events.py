"""Commit-aware dashboard invalidation; events never contain financial data."""
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.db import transaction

logger = logging.getLogger('myfinance')
_pending = ContextVar('investment_changes', default=None)


def dashboard_revision(user_id):
    key = f'investments:dashboard:v1:{user_id}:revision'
    try:
        cache.add(key, uuid.uuid4().hex, timeout=None)
        return cache.get(key)
    except Exception:
        logger.warning(
            'Cache de revisão de investimentos indisponível.', exc_info=True
        )
        return None


def publish_changes(user_ids):
    for user_id in user_ids:
        revision = uuid.uuid4().hex
        try:
            cache.set(
                f'investments:dashboard:v1:{user_id}:revision',
                revision,
                timeout=None,
            )
        except Exception:
            logger.warning(
                'Não foi possível invalidar a revisão de investimentos.',
                exc_info=True,
            )
        try:
            layer = get_channel_layer()
            if layer is not None:
                async_to_sync(layer.group_send)(
                    f'user_updates_{user_id}',
                    {
                        'type': 'investments_changed',
                        'revision': revision,
                    },
                )
        except Exception:
            # The financial transaction has committed; notification failures must
            # not turn a successful write into an apparent failure for the user.
            logger.warning(
                'Não foi possível notificar investimentos.', exc_info=True
            )


def mark_changed(user_id):
    if not user_id:
        return
    pending = _pending.get()
    if pending is not None:
        pending.add(user_id)
    else:
        transaction.on_commit(lambda: publish_changes((user_id,)))


@contextmanager
def investment_atomic():
    """Coalesce signals from a service operation and discard events on rollback."""
    with transaction.atomic():
        parent = _pending.get()
        changed = set()
        token = _pending.set(changed)
        try:
            yield
        except BaseException:
            raise
        else:
            if parent is not None:
                parent.update(changed)
            elif changed:
                owners = tuple(changed)
                transaction.on_commit(lambda: publish_changes(owners))
        finally:
            _pending.reset(token)
