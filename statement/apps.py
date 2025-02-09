from django.apps import AppConfig


class StatementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'statement'

    def ready(self):
        """
        Agenda a execução diária da tarefa `update_index_values` usando o Django Q.
        """
        from django_q.tasks import schedule

        from statement.tasks.finantial_index import update_index_values

        schedule('statement.tasks.finantial_index.update_index_values', schedule_type='D')
