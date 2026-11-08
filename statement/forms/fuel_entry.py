from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from statement.models import FuelEntry
from statement.services.fuel_entries import fuel_history, mark_gap_after
from statement.services.fuel_tracking import FuelTrackingService


class FuelEntryFormMixin:
    """Campos extras do lançamento; persistidos pelo serviço na mesma transação SQL."""

    def setup_fuel_fields(self, user):
        config = FuelTrackingService.get(user)
        self.fuel_subcategory_id = config.subcategory.pk if config and config.active and config.subcategory else None
        try:
            self.existing_fuel_entry = self.instance.fuel_entry if self.instance.pk else None
        except ObjectDoesNotExist:
            self.existing_fuel_entry = None
        self.fuel_history = fuel_history(user, self.instance.pk)
        self.fuel_existing_installment = bool(self.instance.installment_id)
        self.fuel_available = bool(self.fuel_subcategory_id or self.existing_fuel_entry)
        fields = {
            'fuel_tracking_present': forms.BooleanField(required=False, initial=True, widget=forms.HiddenInput),
            'fuel_liters': forms.DecimalField(label='Litros abastecidos', max_digits=10, decimal_places=3,
                                            min_value=Decimal('0.001'), required=False),
            'fuel_price_per_liter': forms.DecimalField(
                label='Preço por litro', max_digits=10, decimal_places=4,
                min_value=Decimal('0.0001'), required=False,
            ),
            'fuel_calculation_basis': forms.ChoiceField(
                choices=[('liters', 'Litros'), ('price', 'Preço por litro')],
                required=False, initial='liters', widget=forms.HiddenInput,
            ),
            'fuel_distance_km': forms.DecimalField(label='Distância desde o abastecimento anterior (km)',
                                                 max_digits=10, decimal_places=1,
                                                 min_value=Decimal('0.1'), required=False),
            'fuel_odometer_km': forms.DecimalField(label='Quilometragem total do veículo (km)',
                                                 max_digits=10, decimal_places=1,
                                                 min_value=Decimal('0'), required=False),
            'fuel_full_tank': forms.TypedChoiceField(label='Completou o tanque?', required=False,
                                                    choices=[('', 'Não informado'), ('True', 'Sim'), ('False', 'Não, abastecimento parcial')],
                                                    coerce=lambda v: v == 'True', empty_value=None, initial='True'),
            'fuel_break_before': forms.BooleanField(label='Houve abastecimento não registrado desde o registro anterior', required=False),
            'fuel_remove': forms.BooleanField(label='Remover os dados deste abastecimento', required=False),
            'fuel_amount_paid': forms.DecimalField(label='Valor total pago pelo abastecimento (todas as parcelas)',
                                                  max_digits=12, decimal_places=2,
                                                  min_value=Decimal('0.01'), required=False),
        }
        for name, field in fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs.setdefault('class', 'form-control')
            self.fields[name] = field
        if self.existing_fuel_entry:
            for name in ('liters', 'distance_km', 'odometer_km', 'full_tank', 'break_before', 'amount_paid'):
                value = getattr(self.existing_fuel_entry, name)
                self.initial[f'fuel_{name}'] = str(value) if name == 'full_tank' and value is not None else value
            price = self.existing_fuel_entry.price_per_liter
            self.initial['fuel_price_per_liter'] = price.quantize(Decimal('0.0001')) if price else None
            self.initial['fuel_calculation_basis'] = (
                'price' if self.existing_fuel_entry.informed_price_per_liter is not None else 'liters'
            )

    def clean_fuel_fields(self, cleaned):
        self.fuel_should_save = False
        if not cleaned.get('fuel_tracking_present'):
            return
        entry = self.existing_fuel_entry
        if cleaned.get('fuel_remove'):
            return
        subcategory = cleaned.get('subcategory')
        selected = subcategory and subcategory.pk == self.fuel_subcategory_id
        has_data = any(cleaned.get(f'fuel_{f}') is not None for f in ('liters', 'price_per_liter', 'distance_km', 'odometer_km'))
        if entry and (not subcategory or subcategory.pk != entry.transaction.subcategory_id) and not selected:
            self.add_error('fuel_remove', 'Marque a remoção dos dados de abastecimento para mudar a subcategoria.')
            return
        if not entry and not selected:
            # Campos ocultos de outra subcategoria não criam abastecimentos.
            return
        if not has_data and not entry:
            return
        if cleaned.get('type', getattr(self, 'transaction_type', None) or self.instance.type) != 'saida':
            self.add_error(None, 'Abastecimentos devem estar associados a uma saída.')
        value = cleaned.get('fuel_amount_paid') if self.fuel_existing_installment else cleaned.get('value')
        self.fuel_informed_price = None
        if value is None or Decimal(str(value)).quantize(Decimal('0.01')) <= 0:
            self.add_error('fuel_amount_paid' if self.fuel_existing_installment else 'value', 'Informe o valor total pago.')
        else:
            self.fuel_total_paid = Decimal(str(value)).quantize(Decimal('0.01'))
            price = cleaned.get('fuel_price_per_liter')
            if price is not None and (cleaned.get('fuel_calculation_basis') == 'price' or cleaned.get('fuel_liters') is None):
                self.fuel_informed_price = price
                try:
                    liters = (self.fuel_total_paid / price).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                    cleaned['fuel_liters'] = self.fields['fuel_liters'].clean(liters)
                except ValidationError as error:
                    self.add_error('fuel_liters', error)
        if cleaned.get('fuel_liters') is None and 'fuel_liters' not in self.errors:
            self.add_error('fuel_liters', 'Informe os litros abastecidos ou o preço por litro.')
        odometer = cleaned.get('fuel_odometer_km')
        posted_date = cleaned.get('posted_date')
        if odometer is not None and posted_date:
            key = (posted_date.isoformat(), self.instance.pk or float('inf'))
            before = [e for e in self.fuel_history if (e['date'], e['id']) < key]
            after = [e for e in self.fuel_history if (e['date'], e['id']) > key]
            previous = next((e for e in reversed(before) if e['odometer'] is not None), None)
            following = next((e for e in after if e['odometer'] is not None), None)
            previous_break = True
            if previous:
                intervening = before[before.index(previous) + 1:]
                previous_break = cleaned.get('fuel_break_before') or any(e['break_before'] for e in intervening)
            next_break = any(e['break_before'] for e in after[:after.index(following) + 1]) if following else True
            if previous and not previous_break and odometer <= previous['odometer']:
                self.add_error('fuel_odometer_km', 'O hodômetro deve ser maior que o registro anterior. Confira a data ou marque a interrupção.')
            if following and not next_break and odometer >= following['odometer']:
                self.add_error('fuel_odometer_km', 'O hodômetro deve ser menor que o próximo registro. Confira a data.')
        self.fuel_should_save = True

    def save_fuel_entry(self, transaction):
        if not self.cleaned_data.get('fuel_tracking_present'):
            return
        if self.cleaned_data.get('fuel_remove'):
            mark_gap_after(transaction)
            FuelEntry.objects.filter(transaction=transaction).delete()
            return
        if not self.fuel_should_save:
            return
        FuelEntry.objects.update_or_create(transaction=transaction, defaults={
            'amount_paid': self.fuel_total_paid,
            'informed_price_per_liter': self.fuel_informed_price,
            **{name: self.cleaned_data.get(f'fuel_{name}') for name in (
                'liters', 'distance_km', 'odometer_km', 'full_tank', 'break_before',
            )},
        })
