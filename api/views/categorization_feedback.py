import os
from datetime import datetime

import requests
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from clients.transaction_classifier import TransactionClassifierClient
from statement.models import CategorizationFeedback
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.views.core.categorization_feedback import CategorizationFeedbackView as StatementView


class CategorizationFeedbackView(BaseView):
    """
    Classe que gerencia a view das cartões na API.
    """

    model = CategorizationFeedback
    service = CategorizationFeedbackService
    serializer = BaseSerializer
    statement_view = StatementView
