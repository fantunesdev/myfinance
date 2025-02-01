from django.utils import timezone

from statement.models import Dream


def create_dream(dream):
    """
    Cria um novo sonho no banco de dados.

    Args:
        dream (Dream): O objeto Dream contendo os dados necessários para a criação de um novo sonho.

    Returns:
        Dream: O objeto Dream recém-criado, com os dados persistidos no banco de dados.

    Raises:
        IntegrityError: Se a criação violar alguma restrição de integridade no banco de dados.
    """
    return Dream.objects.create(
        description=dream.description,
        value=dream.value,
        limit_date=dream.limit_date,
        user=dream.user,
    )


def list_dreams(user):

    """
    Retorna todos os sonhos de um usuário.
    
    Args:
        user (User): O usuário cujos sonhos estão sendo filtrados.
    
    Returns:
        QuerySet: Um conjunto de objetos `Dream` que ainda não venceram.
    """
    return Dream.objects.filter(user=user)


def list_active_dreams(user):
    """
    Retorna todos os sonhos ativos de um usuário (data maior ou igual à data atual).
    
    Args:
        user (User): O usuário cujos sonhos estão sendo filtrados.
    
    Returns:
        QuerySet: Um conjunto de objetos `Dream` que ainda não venceram.
    """
    today = timezone.now() 
    return Dream.objects.filter(user=user, limit_date__gte=today)


def list_past_dreams(user):
    """
    Retorna todos os sonhos que já foram alcançados o que não estão mais ativos 
    (data menor que a data atual).
    
    Args:
        user (User): O usuário cujos sonhos estão sendo filtrados.
    
    Returns:
        QuerySet: Um conjunto de objetos `Dream` que já venceram.
    """
    today = timezone.now()
    return Dream.objects.filter(user=user, limit_date__lt=today)


def list_dream_by_id(id, user):
    """
    Retorna um sonho por id, filtrado pelo usuário.

    Args:
        id (int): Chave primária do sonho a ser recuperado.
        user (User): O usuário cujos sonhos estão sendo filtrados.

    Returns:
        Dream: O objeto Dream correspondente ao id fornecido, se existir e pertencer ao usuário.
        
    Raises:
        DoesNotExist: Se o sonho com o id fornecido não for encontrado ou não pertencer ao usuário.
    """
    return Dream.objects.get(id=id, user=user)


def update_dream(old_dream, new_dream):
    """
    Atualiza um sonho existente com os novos dados fornecidos.

    Args:
        old_dream (Dream): O objeto Dream a ser atualizado.
        new_dream (Dream): O objeto Dream contendo os novos valores para atualização.

    Returns:
        None: A função realiza a atualização no banco de dados e não retorna nada.

    Raises:
        IntegrityError: Se a atualização violar alguma restrição de integridade no banco de dados.
    """
    old_dream.description = new_dream.description
    old_dream.value = new_dream.value
    old_dream.limit_date = new_dream.limit_date
    old_dream.user = new_dream.user
    old_dream.save(force_update=True)


def delete_dream(dream):
    """
    Deleta um sonho do banco de dados.

    Args:
        dream (Dream): O objeto Dream a ser deletado.

    Returns:
        None: A função deleta o sonho e não retorna nada.

    Raises:
        ProtectedError: Se o sonho estiver protegido por alguma restrição de exclusão no banco de dados (ex.: se existir dependências de integridade referencial).
    """
    dream.delete()
