import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.models import Version
from statement.services import category_services


def get_defaults():
    """
    Obtém configurações padrão, incluindo a versão mais recente e o ano atual.

    Returns:
    Um dicionário contendo as configurações padrão:
    - 'version': A versão mais recente.
    - 'year': O ano atual.

    Raises:
    Http404: Se não for possível encontrar a versão mais recente.
    """
    try:
        version = Version.objects.latest('id')
        defaults = {
            'version': version.version,
            'year': datetime.datetime.today().year,
        }
        return defaults
    except ObjectDoesNotExist:
        raise Http404
