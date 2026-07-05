import uuid
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.base import InvestmentBaseService

DEFAULT_WALLET_BROKER_DESCRIPTION = 'Caixa de investimentos'
DEFAULT_WALLET_ASSET_DESCRIPTION = 'Disponível para investir'
DEFAULT_WALLET_ASSET_SYMBOL = 'CASH-BRL'
DEFAULT_WALLET_INVESTMENT_DESCRIPTION = 'Caixa de investimentos BRL'


class InvestmentTransactionService(InvestmentBaseService):
    model = InvestmentTransaction

    @classmethod
    @transaction.atomic
    def create(cls, form, user=None, id=None):
        instance = form.save(commit=False)
        instance = cls.verify_user_field(instance, user)
        cls.set_default_due_date(instance)
        instance.save()
        cls.sync_manual_wallet_counterpart(instance)
        return instance

    @classmethod
    @transaction.atomic
    def update(cls, form, instance):
        original_instance = cls.model.objects.get(pk=instance.pk)
        cls.set_default_due_date(form.instance)
        instance = super().update(form, instance)

        original_counterpart_type = cls._manual_wallet_counterpart_type(original_instance)
        current_counterpart_type = cls._manual_wallet_counterpart_type(instance)
        if original_counterpart_type and original_counterpart_type != current_counterpart_type:
            cls.delete_manual_wallet_counterpart(original_instance, transaction_type=original_counterpart_type)

        cls.sync_manual_wallet_counterpart(instance)
        return instance

    @classmethod
    @transaction.atomic
    def delete(cls, instance):
        counterpart_type = cls._manual_wallet_counterpart_type(instance)
        if counterpart_type:
            cls.delete_manual_wallet_counterpart(instance, transaction_type=counterpart_type)
        return super().delete(instance)

    @classmethod
    def get_default_wallet(cls, user):
        try:
            return Investment.objects.select_related('asset', 'broker').get(
                description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
                asset__symbol=DEFAULT_WALLET_ASSET_SYMBOL,
                broker__description=DEFAULT_WALLET_BROKER_DESCRIPTION,
                user=user,
            )
        except Investment.DoesNotExist:
            return None

    @classmethod
    def get_or_create_default_wallet(cls, user):
        broker, _ = Broker.objects.get_or_create(
            description=DEFAULT_WALLET_BROKER_DESCRIPTION,
            user=user,
            defaults={'kind': 'wallet'},
        )
        asset, _ = Asset.objects.get_or_create(
            description=DEFAULT_WALLET_ASSET_DESCRIPTION,
            symbol=DEFAULT_WALLET_ASSET_SYMBOL,
            user=user,
            defaults={
                'asset_type': 'currency',
                'income_behavior': 'none',
                'currency': 'BRL',
            },
        )
        investment, _ = Investment.objects.get_or_create(
            description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
            asset=asset,
            broker=broker,
            user=user,
            defaults={
                'start_date': timezone.localdate(),
                'status': 'active',
            },
        )
        return investment

    @classmethod
    @transaction.atomic
    def create_wallet_contribution_from_statement_transaction(cls, statement_transaction, wallet=None, notes=''):
        existing_contribution = cls._get_statement_investment_transaction(statement_transaction)
        if existing_contribution:
            return existing_contribution

        user = statement_transaction.user
        wallet = wallet or cls.get_or_create_default_wallet(user)
        if wallet.user_id != user.id:
            raise ValueError('A wallet deve pertencer ao mesmo usuário da transação financeira.')

        amount = cls._absolute_amount(statement_transaction.value)
        cls._validate_positive_amount(amount)

        return cls.model.objects.create(
            investment=wallet,
            date=statement_transaction.payment_date,
            type='aporte',
            amount=amount,
            statement_transaction=statement_transaction,
            notes=notes or statement_transaction.description,
            user=user,
        )

    @classmethod
    @transaction.atomic
    def sync_wallet_contribution_from_statement_transaction(cls, statement_transaction):
        existing_contribution = cls._get_statement_investment_transaction(statement_transaction)

        if not cls._should_sync_statement_transaction(statement_transaction):
            if existing_contribution:
                existing_contribution.delete()
            return None

        wallet = cls.get_or_create_default_wallet(statement_transaction.user)
        amount = cls._absolute_amount(statement_transaction.value)
        cls._validate_positive_amount(amount)

        if existing_contribution:
            existing_contribution.investment = wallet
            existing_contribution.date = statement_transaction.payment_date
            existing_contribution.type = 'aporte'
            existing_contribution.amount = amount
            existing_contribution.notes = statement_transaction.description
            existing_contribution.user = statement_transaction.user
            existing_contribution.save(
                update_fields=[
                    'investment',
                    'date',
                    'type',
                    'amount',
                    'notes',
                    'user',
                ]
            )
            return existing_contribution

        return cls.create_wallet_contribution_from_statement_transaction(statement_transaction, wallet=wallet)

    @classmethod
    @transaction.atomic
    def transfer_between_investments(
        cls,
        source,
        destination,
        amount,
        date=None,
        due_date=None,
        quantity=None,
        unit_price=None,
        notes='',
    ):
        if source.id == destination.id:
            raise ValueError('Os investimentos de origem e destino devem ser diferentes.')

        if source.user_id != destination.user_id:
            raise ValueError('Os investimentos devem pertencer ao mesmo usuário.')

        operation_id = uuid.uuid4()
        transaction_date = date or timezone.localdate()
        amount = cls._absolute_amount(amount)
        cls._validate_positive_amount(amount)

        source_transaction = cls.model.objects.create(
            investment=source,
            date=transaction_date,
            type='resgate',
            amount=amount,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
        )
        destination_transaction = cls.model.objects.create(
            investment=destination,
            date=transaction_date,
            due_date=due_date or destination.due_date,
            type='aporte',
            amount=amount,
            quantity=quantity,
            unit_price=unit_price,
            operation_id=operation_id,
            notes=notes,
            user=destination.user,
        )
        return source_transaction, destination_transaction

    @classmethod
    @transaction.atomic
    def redeem_to_wallet(
        cls,
        source,
        gross_amount,
        principal_amount,
        date=None,
        quantity=None,
        unit_price=None,
        notes='',
    ):
        wallet = cls.get_or_create_default_wallet(source.user)
        if source.id == wallet.id:
            raise ValueError('A carteira default não pode ser resgatada para ela mesma.')

        operation_id = uuid.uuid4()
        transaction_date = date or timezone.localdate()
        gross_amount = cls._absolute_amount(gross_amount)
        principal_amount = cls._absolute_amount(principal_amount)
        cls._validate_positive_amount(gross_amount)
        cls._validate_positive_amount(principal_amount)

        created_transactions = []
        result_amount = gross_amount - principal_amount
        if result_amount > Decimal('0'):
            created_transactions.append(
                cls.model.objects.create(
                    investment=source,
                    date=transaction_date,
                    type='rendimento',
                    amount=result_amount,
                    operation_id=operation_id,
                    notes=notes,
                    user=source.user,
                )
            )
        elif result_amount < Decimal('0'):
            created_transactions.append(
                cls.model.objects.create(
                    investment=source,
                    date=transaction_date,
                    type='custo',
                    amount=abs(result_amount),
                    operation_id=operation_id,
                    notes=notes,
                    user=source.user,
                )
            )

        source_transaction = cls.model.objects.create(
            investment=source,
            date=transaction_date,
            type='resgate',
            amount=gross_amount,
            quantity=quantity,
            unit_price=unit_price,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
        )
        wallet_transaction = cls.model.objects.create(
            investment=wallet,
            date=transaction_date,
            type='aporte',
            amount=gross_amount,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
        )
        created_transactions.extend([source_transaction, wallet_transaction])
        return created_transactions

    @classmethod
    def sync_manual_wallet_counterpart(cls, instance):
        wallet_transaction_type = cls._manual_wallet_counterpart_type(instance)
        if not wallet_transaction_type:
            return None

        wallet = cls.get_or_create_default_wallet(instance.user)
        operation_id = instance.operation_id or uuid.uuid4()
        if not instance.operation_id:
            instance.operation_id = operation_id
            instance.save(update_fields=['operation_id'])

        wallet_transaction = (
            cls.model.objects.filter(operation_id=operation_id, type=wallet_transaction_type, investment=wallet)
            .exclude(id=instance.id)
            .first()
        )
        notes = instance.notes or cls._get_wallet_counterpart_notes(instance)

        if wallet_transaction:
            wallet_transaction.date = instance.date
            wallet_transaction.due_date = None
            wallet_transaction.amount = instance.amount
            wallet_transaction.notes = notes
            wallet_transaction.user = instance.user
            wallet_transaction.save(update_fields=['date', 'due_date', 'amount', 'notes', 'user'])
            return wallet_transaction

        return cls.model.objects.create(
            investment=wallet,
            date=instance.date,
            due_date=None,
            type=wallet_transaction_type,
            amount=instance.amount,
            operation_id=operation_id,
            notes=notes,
            user=instance.user,
        )

    @classmethod
    def delete_manual_wallet_counterpart(cls, instance, transaction_type=None, clear_operation_id=False):
        if not instance.operation_id:
            return

        wallet = cls.get_default_wallet(instance.user)
        if wallet:
            queryset = cls.model.objects.filter(operation_id=instance.operation_id, investment=wallet).exclude(id=instance.id)
            if transaction_type:
                queryset = queryset.filter(type=transaction_type)
            queryset.delete()

        if clear_operation_id and instance.pk:
            instance.operation_id = None
            instance.save(update_fields=['operation_id'])

    @staticmethod
    def _absolute_amount(value):
        return abs(Decimal(str(value or 0)))

    @staticmethod
    def set_default_due_date(instance):
        if instance.type == 'aporte' and not instance.due_date and instance.investment_id:
            instance.due_date = instance.investment.due_date

    @staticmethod
    def _validate_positive_amount(amount):
        if amount <= Decimal('0'):
            raise ValueError('O valor deve ser maior que zero.')

    @staticmethod
    def _get_statement_investment_transaction(statement_transaction):
        try:
            return statement_transaction.investment_transaction
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def _should_sync_statement_transaction(statement_transaction):
        subcategory = getattr(statement_transaction, 'subcategory', None)
        return (
            getattr(statement_transaction, 'type', None) == 'saida'
            and bool(subcategory)
            and bool(getattr(subcategory, 'is_investment', False))
        )

    @classmethod
    def _needs_manual_wallet_counterpart(cls, instance):
        return cls._manual_wallet_counterpart_type(instance) is not None

    @classmethod
    def _manual_wallet_counterpart_type(cls, instance):
        if instance.type not in ['aporte', 'resgate']:
            return None
        if instance.statement_transaction_id:
            return None
        if not instance.user_id:
            return None

        wallet = cls.get_default_wallet(instance.user)
        if wallet and instance.investment_id == wallet.id:
            return None

        return 'resgate' if instance.type == 'aporte' else 'aporte'

    @staticmethod
    def _get_wallet_counterpart_notes(instance):
        if instance.type == 'aporte':
            return f'Transferência para {instance.investment}'
        return f'Transferência de {instance.investment}'
