from typing import Iterable, List, Set

from django.db import transaction

from statement.models import NotificationTitle, NotificationTitlePreference


class NotificationTitleService:
    @staticmethod
    def ensure_titles(titles: Iterable[str]) -> List[NotificationTitle]:
        """Cria registros `NotificationTitle` ausentes para os títulos fornecidos."""
        results = []
        existing = {nt.title: nt for nt in NotificationTitle.objects.filter(title__in=titles)}
        for t in titles:
            if not t:
                continue
            nt = existing.get(t)
            if not nt:
                nt = NotificationTitle.objects.create(title=t)
            results.append(nt)
        return results

    @staticmethod
    def get_all_titles() -> List[NotificationTitle]:
        return list(NotificationTitle.objects.all())

    @staticmethod
    def get_enabled_titles_for_user(user) -> Set[str]:
        """Retorna um conjunto com os títulos habilitados para o usuário.

        Se não houver preferência registrada para um título, ele é considerado desabilitado.
        """
        prefs = NotificationTitlePreference.objects.filter(user=user, enabled=True).select_related('title')
        return {p.title.title for p in prefs}

    @staticmethod
    @transaction.atomic
    def set_user_enabled_titles(user, enabled_title_ids: Iterable[int]):
        """Atualiza as preferências de títulos do usuário.

        `enabled_title_ids` é um iterável com ids de `NotificationTitle` que devem
        ficar habilitados para o usuário. Todos os outros títulos serão marcados
        como desabilitados para esse usuário.
        """
        enabled_ids = set(int(i) for i in enabled_title_ids) if enabled_title_ids else set()

        # Garante que exista uma preferência para todos os títulos
        all_titles = list(NotificationTitle.objects.all())
        existing_prefs = { (p.user_id, p.title_id): p for p in NotificationTitlePreference.objects.filter(user=user) }

        # Create missing prefs and update enabled flag
        for title in all_titles:
            pref, created = NotificationTitlePreference.objects.get_or_create(user=user, title=title)
            should_enable = title.id in enabled_ids
            if pref.enabled != should_enable:
                pref.enabled = should_enable
                pref.save(update_fields=['enabled'])
