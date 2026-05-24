from investments.models import Asset
from investments.services.base import InvestmentBaseService


class AssetService(InvestmentBaseService):
    model = Asset
