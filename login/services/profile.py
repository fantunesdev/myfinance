from login.models import Profile
from statement.services.base_service import BaseService
from statement.services.core.account import AccountService
from statement.services.core.card import CardService

class ProfileService:
    """ Serviço para gerenciar operações relacionadas ao perfil do usuário. """

    def __init__(self, user):
        self.user = user
        self.configs = Profile.objects.filter(user=user).first()
        self._crud = BaseService
        self._crud.model = Profile
        self._crud.user_field = 'user'

    @property
    def accounts(self):
        """ Retorna todas as contas do usuário. """
        return AccountService.get_all(self.user)

    @property
    def cards(self):
        """ Retorna todos os cartões do usuário. """
        return CardService.get_all(self.user)

    # Métodos CRUD
    def create(self, form):
        """
        Cria um novo perfil de usuário.
        :param form: Formulário com os dados do perfil.
        :return: Instância do perfil criado.
        """
        return self._crud.create(form, user=self.user)

    def update(self, form, instance):
        """
        Atualiza um perfil de usuário existente.
        :param form: Formulário com os dados atualizados.
        :param instance: Instância do perfil a ser atualizado.
        :return: Instância do perfil atualizado.
        """
        return self._crud.update(form, instance)

    def delete(self, instance):
        """ Deleta um perfil de usuário existente.
        :param instance: Instância do perfil a ser deletado.
        :return: Instância do perfil deletado.
        """
        return self._crud.delete(instance)

    def get_by_id(self, id):
        """
        Retorna um perfil de usuário pelo ID.
        :param id: ID do perfil a ser buscado.
        :return: Instância do perfil encontrado.
        """
        return self._crud.get_by_id(id, user=self.user)

    def get_all(self):
        """
        Retorna todos os perfis de usuário.
        :return: Lista de instâncias de perfis encontrados.
        """
        return self._crud.get_all(user=self.user)
