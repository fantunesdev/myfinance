from investments.models import Broker
from investments.services.base import InvestmentBaseService


class BrokerService(InvestmentBaseService):
    model = Broker
