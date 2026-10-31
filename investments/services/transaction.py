import uuid
from decimal import Decimal, InvalidOperation
from itertools import groupby

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.base import InvestmentBaseService
from investments.services.investment import InvestmentService
from login.models import User

DEFAULT_WALLET_BROKER_DESCRIPTION = 'Caixa de investimentos'
DEFAULT_WALLET_ASSET_DESCRIPTION = 'Disponível para investir'
DEFAULT_WALLET_ASSET_SYMBOL = 'CASH-BRL'
DEFAULT_WALLET_INVESTMENT_DESCRIPTION = 'Caixa de investimentos BRL'


class InvestmentTransactionService(InvestmentBaseService):
    model = InvestmentTransaction

    @staticmethod
    def lock_user(user):
        # All investment writes for one owner use the same lock, including wallet creation.
        User.objects.select_for_update().get(pk=user.pk)

    @classmethod
    @transaction.atomic
    def create(cls, form, user=None, id=None):
        cls.lock_user(user)
        instance = form.save(commit=False)
        instance.user = user
        cls.set_default_due_date(instance)
        instance.full_clean()
        wallet = cls.get_or_create_default_wallet(user)
        if instance.type == 'resgate' and instance.investment_id != wallet.pk:
            position = InvestmentService.get_position(instance.investment, as_of=instance.date)
            if instance.amount > position['value'] or position['value'] <= 0:
                raise ValidationError('Saldo insuficiente para resgatar nesta data.')
            instance.redemption_principal = (
                position['remaining_principal'] * instance.amount / position['value']
            ).quantize(Decimal('0.01'))
        instance.save()
        cls.sync_manual_wallet_counterpart(instance)
        cls.validate_balances(instance.user, [instance.investment_id])
        return instance

    @classmethod
    @transaction.atomic
    def update(cls, form, instance):
        original = cls.model.objects.get(pk=instance.pk)
        cls.lock_user(original.user)
        original.refresh_from_db()
        instance = form.save(commit=False)
        instance.user = original.user
        if original.statement_transaction_id:
            raise ValidationError('Este aporte vem do extrato. Edite o lançamento financeiro de origem.')
        if original.operation_id:
            members = cls.operation_members(original)
            if (
                len(members) != 2
                or any(item.redemption_principal is not None for item in members)
                or {item.type for item in members} != {'aporte', 'resgate'}
            ):
                raise ValidationError(
                    'Este lançamento faz parte de um resgate composto. Exclua a operação completa e registre o resgate novamente.'
                )
            if instance.type != original.type or instance.investment_id != original.investment_id:
                raise ValidationError(
                    'O tipo e o investimento de uma transferência não podem ser alterados isoladamente. Exclua e refaça a operação.'
                )
            counterpart = next(item for item in members if item.pk != original.pk)
            instance.full_clean()
            instance.save()
            counterpart.amount = instance.amount
            counterpart.date = instance.date
            counterpart.notes = instance.notes
            counterpart.full_clean()
            counterpart.save()
            for item in (instance, counterpart):
                cls.validate_funding(item)
            cls.validate_balances(original.user, [item.investment_id for item in members])
            return instance
        instance.full_clean()
        instance.save()
        if (original.type, original.investment_id, original.amount) != (
            instance.type,
            instance.investment_id,
            instance.amount,
        ):
            cls.sync_manual_wallet_counterpart(instance)
        cls.validate_funding(instance)
        cls.validate_balances(original.user, [original.investment_id, instance.investment_id])
        return instance

    @classmethod
    @transaction.atomic
    def delete(cls, instance):
        cls.lock_user(instance.user)
        instance = cls.model.objects.get(pk=instance.pk)
        if instance.statement_transaction_id:
            raise ValidationError('Este aporte vem do extrato. Exclua ou altere o lançamento financeiro de origem.')
        members = cls.operation_members(instance) if instance.operation_id else [instance]
        ids = [item.pk for item in members]
        if cls.model.objects.filter(funding_transaction_id__in=ids).exclude(pk__in=ids).exists():
            raise ValidationError(
                'Esta movimentação financia outra aplicação. Desfaça a aplicação dependente primeiro.'
            )
        investments = [item.investment_id for item in members]
        cls.model.objects.filter(pk__in=ids, user=instance.user).delete()
        cls.validate_balances(instance.user, investments)

    @classmethod
    def operation_members(cls, instance):
        # External funding is never a transfer leg, including legacy shared UUIDs.
        members = list(
            cls.model.objects.filter(
                operation_id=instance.operation_id,
                user=instance.user,
                statement_transaction__isnull=True,
            ).order_by('id')
        )
        if sum(item.type == 'aporte' for item in members) != 1 or sum(item.type == 'resgate' for item in members) != 1:
            raise ValidationError(
                'Esta operação tem vínculos inconsistentes e precisa ser revisada antes de editar ou excluir.'
            )
        return members

    @classmethod
    def get_default_wallet(cls, user):
        return Investment.objects.select_related('asset', 'broker').filter(default_wallet_for=user, user=user).first()

    @classmethod
    @transaction.atomic
    def get_or_create_default_wallet(cls, user):
        cls.lock_user(user)
        wallet = cls.get_default_wallet(user)
        if wallet:
            return wallet
        candidates = list(
            Investment.objects.filter(user=user).filter(
                Q(description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION) | Q(asset__symbol=DEFAULT_WALLET_ASSET_SYMBOL)
            )
        )
        if len(candidates) > 1:
            raise ValidationError(
                'Há mais de um possível caixa de investimentos. Identifique o caixa padrão antes de movimentar.'
            )
        if candidates:
            wallet = candidates[0]
            wallet.default_wallet_for = user
            wallet.save(update_fields=['default_wallet_for'])
            return wallet
        broker, _ = Broker.objects.get_or_create(
            description=DEFAULT_WALLET_BROKER_DESCRIPTION,
            user=user,
            defaults={'kind': 'wallet'},
        )
        asset, _ = Asset.objects.get_or_create(
            description=DEFAULT_WALLET_ASSET_DESCRIPTION,
            symbol=DEFAULT_WALLET_ASSET_SYMBOL,
            user=user,
            defaults={'asset_type': 'currency', 'income_behavior': 'none', 'currency': 'BRL'},
        )
        return Investment.objects.create(
            description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
            asset=asset,
            broker=broker,
            user=user,
            default_wallet_for=user,
            start_date=timezone.localdate(),
            status='active',
        )

    @classmethod
    @transaction.atomic
    def create_wallet_contribution_from_statement_transaction(cls, statement_transaction, wallet=None, notes=''):
        return cls.sync_wallet_contribution_from_statement_transaction(statement_transaction)

    @classmethod
    @transaction.atomic
    def sync_wallet_contribution_from_statement_transaction(cls, statement_transaction):
        cls.lock_user(statement_transaction.user)
        existing = cls.model.objects.filter(statement_transaction_id=statement_transaction.pk).first()
        if not cls._should_sync_statement_transaction(statement_transaction):
            if existing:
                cls.remove_statement_contribution(statement_transaction)
            return None
        wallet = cls.get_or_create_default_wallet(statement_transaction.user)
        amount = cls.statement_amount(statement_transaction.value)
        if existing:
            financial_change = existing.amount != amount or existing.date != statement_transaction.payment_date
            existing.amount = amount
            existing.date = statement_transaction.payment_date
            existing.notes = statement_transaction.description
            existing.full_clean()
            cls.validate_funding(existing)
            existing.save(update_fields=['amount', 'date', 'notes'])
            if financial_change:
                cls.validate_balances(statement_transaction.user, [wallet.pk])
            return existing
        instance = cls.model.objects.create(
            investment=wallet,
            date=statement_transaction.payment_date,
            type='aporte',
            amount=amount,
            statement_transaction=statement_transaction,
            notes=statement_transaction.description,
            user=statement_transaction.user,
        )
        return instance

    @classmethod
    @transaction.atomic
    def remove_statement_contribution(cls, statement_transaction):
        cls.lock_user(statement_transaction.user)
        existing = cls.model.objects.filter(statement_transaction_id=statement_transaction.pk).first()
        if not existing:
            return
        if existing.funded_transactions.exists() or existing.operation_id:
            raise ValidationError(
                'Este lançamento já financia uma aplicação. Desfaça a aplicação antes de excluir ou recategorizar a origem.'
            )
        wallet_id = existing.investment_id
        existing.delete()
        cls.validate_balances(statement_transaction.user, [wallet_id])

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
        funding_transaction=None,
    ):
        if source.pk == destination.pk or source.user_id != destination.user_id:
            raise ValidationError('Origem e destino devem ser diferentes e pertencer ao mesmo usuário.')
        cls.lock_user(source.user)
        source = Investment.objects.get(pk=source.pk, user_id=source.user_id)
        destination = Investment.objects.get(pk=destination.pk, user_id=source.user_id)
        amount = cls.positive_amount(amount)
        transaction_date = date or timezone.localdate()
        if source.status != 'active' or destination.status != 'active':
            raise ValidationError('Use investimentos ativos para movimentar.')
        if funding_transaction:
            funding_transaction = cls.model.objects.get(pk=funding_transaction.pk, user=source.user)
            if funding_transaction.investment_id != source.pk or funding_transaction.type != 'aporte':
                raise ValidationError('A origem deve ser um aporte do caixa.')
            # Applying a particular funding entry is a single operation; retrying POST must not apply it twice.
            if funding_transaction.funded_transactions.exists():
                raise ValidationError('Este aporte já foi aplicado. Edite ou desfaça a aplicação existente.')
            if amount > funding_transaction.amount or transaction_date < funding_transaction.date:
                raise ValidationError('O valor e a data devem respeitar o aporte de origem.')
        position = InvestmentService.get_position(source, as_of=transaction_date)
        if amount > position['value']:
            raise ValidationError('Saldo insuficiente na origem para esta data.')
        operation_id = uuid.uuid4()
        debit = cls.model(
            investment=source,
            date=transaction_date,
            type='resgate',
            amount=amount,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
        )
        credit = cls.model(
            investment=destination,
            date=transaction_date,
            due_date=due_date or destination.due_date,
            type='aporte',
            amount=amount,
            quantity=quantity,
            unit_price=unit_price,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
            funding_transaction=funding_transaction,
        )
        debit.full_clean()
        credit.full_clean()
        debit.save()
        credit.save()
        cls.validate_balances(source.user, [source.pk, destination.pk])
        return debit, credit

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
        cls.lock_user(source.user)
        source = Investment.objects.get(pk=source.pk, user_id=source.user_id)
        wallet = cls.get_or_create_default_wallet(source.user)
        if source.pk == wallet.pk or source.status != 'active':
            raise ValidationError('Escolha um investimento ativo diferente do caixa para resgatar.')
        gross_amount = cls.positive_amount(gross_amount)
        principal_amount = cls.positive_amount(principal_amount)
        transaction_date = date or timezone.localdate()
        position = InvestmentService.get_position(source, as_of=transaction_date)
        remaining = position['remaining_principal']
        if remaining <= 0 or principal_amount > remaining:
            raise ValidationError('O principal resgatado excede o principal ainda aplicado nesta data.')
        if quantity is not None and (quantity <= 0 or quantity > position['quantity']):
            raise ValidationError('Quantidade de resgate inválida ou superior à posição.')
        fraction = principal_amount / remaining
        allocated_value = (position['value'] * fraction).quantize(Decimal('0.01'))
        known_income = (position['unwithdrawn_income'] * fraction).quantize(Decimal('0.01'))
        new_result = gross_amount - principal_amount - known_income
        operation_id = uuid.uuid4()
        common = dict(
            investment=source, date=transaction_date, operation_id=operation_id, notes=notes, user=source.user
        )
        records = []
        if new_result:
            records.append(
                cls.model.objects.create(
                    **common,
                    type='rendimento' if new_result > 0 else 'custo',
                    amount=abs(new_result),
                )
            )
        # A prior valuation already contains unrealized gains/losses. Recognize the
        # result without adding those gains a second time to the portfolio value.
        target_before_withdrawal = position['value'] - allocated_value + gross_amount
        if position['value'] + new_result != target_before_withdrawal:
            records.append(
                cls.model.objects.create(
                    **common,
                    type='atualizacao',
                    amount=0,
                    current_value=target_before_withdrawal,
                )
            )
        debit = cls.model(
            **common,
            type='resgate',
            amount=gross_amount,
            redemption_principal=principal_amount,
            quantity=quantity,
            unit_price=unit_price,
        )
        debit.full_clean()
        debit.save()
        credit = cls.model.objects.create(
            investment=wallet,
            date=transaction_date,
            type='aporte',
            amount=gross_amount,
            operation_id=operation_id,
            notes=notes,
            user=source.user,
        )
        records.extend([debit, credit])
        cls.validate_balances(source.user, [source.pk, wallet.pk])
        return records

    @classmethod
    def sync_manual_wallet_counterpart(cls, instance):
        if instance.type not in ('aporte', 'resgate') or instance.statement_transaction_id:
            return None
        wallet = cls.get_or_create_default_wallet(instance.user)
        if instance.investment_id == wallet.pk:
            return None
        if instance.operation_id:
            raise ValidationError('A movimentação já pertence a uma operação.')
        instance.operation_id = uuid.uuid4()
        instance.save(update_fields=['operation_id'])
        return cls.model.objects.create(
            investment=wallet,
            date=instance.date,
            type='resgate' if instance.type == 'aporte' else 'aporte',
            amount=instance.amount,
            operation_id=instance.operation_id,
            notes=instance.notes or f'Transferência: {instance.investment}',
            user=instance.user,
        )

    @classmethod
    def validate_funding(cls, instance):
        if instance.funding_transaction_id:
            funding = cls.model.objects.get(pk=instance.funding_transaction_id)
            if instance.user_id != funding.user_id or instance.date < funding.date:
                raise ValidationError('A aplicação deve respeitar o usuário e a data do aporte de origem.')
            used = sum((item.amount for item in funding.funded_transactions.all()), Decimal('0'))
            if used > funding.amount:
                raise ValidationError('A aplicação excede o aporte de origem.')
        funded = list(instance.funded_transactions.all())
        if funded and (
            sum((item.amount for item in funded), Decimal('0')) > instance.amount
            or any(item.date < instance.date for item in funded)
        ):
            raise ValidationError(
                'Este aporte já foi aplicado. Desfaça ou ajuste a aplicação antes de reduzir o valor ou alterar sua data.'
            )

    @classmethod
    def validate_balances(cls, user, investment_ids):
        wallet = cls.get_default_wallet(user)
        ids = set(investment_ids)
        if wallet:
            ids.add(wallet.pk)
        for investment in Investment.objects.filter(pk__in=ids, user=user):
            value = quantity = Decimal('0')
            movements = investment.transactions.filter(user=user).order_by('date', 'id')
            for day, daily in groupby(movements, key=lambda item: item.date):
                for movement in daily:
                    value = InvestmentService.apply_value(value, movement)
                    if movement.type == 'aporte':
                        quantity += movement.quantity or Decimal('0')
                    elif movement.type == 'resgate':
                        quantity -= movement.quantity or Decimal('0')
                if value < 0 or quantity < 0:
                    raise ValidationError(
                        f'A operação deixaria saldo ou quantidade negativos em {investment} em {day:%d/%m/%Y}.'
                    )

    @staticmethod
    def positive_amount(value):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError('Informe um valor válido.')
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            raise ValidationError('O valor deve ser positivo, com até duas casas decimais.')
        if amount >= Decimal('1000000000000'):
            raise ValidationError('O valor excede o limite permitido.')
        return amount

    @classmethod
    def statement_amount(cls, value):
        # Statement expenses historically accept either sign. This conversion is
        # deliberately limited to that existing integration, never to manual movements.
        return cls.positive_amount(abs(Decimal(str(value))).quantize(Decimal('0.01')))

    @staticmethod
    def set_default_due_date(instance):
        if instance.type == 'aporte' and not instance.due_date and instance.investment_id:
            instance.due_date = instance.investment.due_date

    @staticmethod
    def _should_sync_statement_transaction(statement_transaction):
        subcategory = getattr(statement_transaction, 'subcategory', None)
        return (
            getattr(statement_transaction, 'type', None) == 'saida'
            and bool(subcategory)
            and bool(getattr(subcategory, 'is_investment', False))
        )
