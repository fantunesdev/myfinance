from statement.forms.base_form import BaseForm
from statement.models import FixedIncomeSecurity


class FixedIncomeSecurityForm(BaseForm):
    class Meta:
        model = FixedIncomeSecurity
        fields = '__all__'
        exclude = ['user']
