import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.models import Version
from statement.services import category_services


def get_defaults():
    try:
        version = Version.objects.latest('id')
        defaults = {
            'version': version.version,
            'year': datetime.datetime.today().year,
        }
        return defaults
    except ObjectDoesNotExist:
        raise Http404
