from django.conf import settings
from django.db import models


class BankConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    item_id = models.UUIDField(unique=True)
    status = models.CharField(max_length=40, blank=True)
    consent_expires_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    prefer_pluggy = models.BooleanField(default=False)


class ExternalAccount(models.Model):
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name="accounts")
    external_id = models.UUIDField(unique=True)
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3)
    used_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    card = models.ForeignKey("statement.Card", null=True, blank=True, on_delete=models.PROTECT)


class ExternalCardIdentifier(models.Model):
    account = models.ForeignKey(ExternalAccount, on_delete=models.CASCADE, related_name="identifiers")
    last_four = models.CharField(max_length=4)
    card_number = models.ForeignKey("statement.CardNumber", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "last_four"], name="pluggy_account_final_unique")]


class ExternalBill(models.Model):
    account = models.ForeignKey(ExternalAccount, on_delete=models.CASCADE, related_name="bills")
    external_id = models.UUIDField(unique=True)
    due_date = models.DateField(null=True)
    closing_date = models.DateField(null=True)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)


class ExternalTransaction(models.Model):
    account = models.ForeignKey(ExternalAccount, on_delete=models.CASCADE, related_name="transactions")
    external_id = models.UUIDField(unique=True)
    # Normalized, minimal source facts. No credentials, payer documents, or full PAN.
    facts = models.JSONField()
    suggestion = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True)
    revision = models.PositiveIntegerField(default=1)
    state = models.CharField(
        max_length=12,
        default="new",
        choices=[
            ("new", "Revisar"),
            ("imported", "Importado"),
            ("linked", "Vinculado"),
            ("ignored", "Ignorado"),
            ("conflict", "Alteração na fonte"),
        ],
    )
    transaction = models.ForeignKey(
        "statement.Transaction", null=True, blank=True, on_delete=models.PROTECT, related_name="bank_sync_links"
    )


class ProjectedInstallment(models.Model):
    account = models.ForeignKey(ExternalAccount, on_delete=models.PROTECT)
    anchor = models.ForeignKey(ExternalTransaction, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    number = models.PositiveIntegerField()
    transaction = models.OneToOneField("statement.Transaction", on_delete=models.CASCADE)
    confirmed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["anchor", "number"], name="pluggy_projection_number_unique")]


class SyncRun(models.Model):
    connection = models.ForeignKey(BankConnection, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    state = models.CharField(max_length=12, default="running")
    message = models.CharField(max_length=255, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)


class ExternalInvestment(models.Model):
    connection = models.ForeignKey(BankConnection, on_delete=models.PROTECT, related_name='investments')
    external_id = models.UUIDField()
    investment = models.OneToOneField('investments.Investment', null=True, blank=True, on_delete=models.PROTECT, related_name='pluggy_source')
    facts = models.JSONField(default=dict)
    reference_at = models.DateTimeField(null=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'external_id'], name='unique_pluggy_investment')]


class InvestmentSyncRun(models.Model):
    connection = models.ForeignKey(BankConnection, on_delete=models.PROTECT, related_name='investment_runs')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    state = models.CharField(max_length=16, default='running')
    summary = models.JSONField(default=dict)
    message = models.CharField(max_length=255, blank=True)


class InvestmentSnapshot(models.Model):
    external = models.ForeignKey(ExternalInvestment, on_delete=models.PROTECT, related_name='snapshots')
    reference_at = models.DateTimeField()
    fingerprint = models.CharField(max_length=64)
    facts = models.JSONField()
    movement = models.OneToOneField('investments.InvestmentTransaction', null=True, on_delete=models.PROTECT, related_name='pluggy_snapshot')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['external', 'reference_at', 'fingerprint'], name='unique_investment_snapshot')]


class InvestmentReconciliationBaseline(models.Model):
    investment = models.OneToOneField('investments.Investment', on_delete=models.PROTECT, related_name='reconciliation_baseline')
    date = models.DateField()
    evidence = models.TextField()


class InvestmentEvent(models.Model):
    last_seen_job = models.ForeignKey('InvestmentHistoryJob', null=True, on_delete=models.PROTECT)
    connection = models.ForeignKey(BankConnection, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=128)
    investments = models.ManyToManyField(ExternalInvestment)
    facts = models.JSONField()
    revision = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=20, default='new')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'external_id'], name='unique_investment_event')]


class InvestmentEventRevision(models.Model):
    event = models.ForeignKey(InvestmentEvent, on_delete=models.PROTECT, related_name='revisions')
    revision = models.PositiveIntegerField()
    facts = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'revision'], name='unique_investment_event_revision')]


class ReconciledInvestmentOperation(models.Model):
    event = models.OneToOneField(InvestmentEvent, on_delete=models.PROTECT, related_name='operation')
    kind = models.CharField(max_length=24)
    state = models.CharField(max_length=20)
    evidence = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    movements = models.ManyToManyField('investments.InvestmentTransaction', related_name='reconciled_operations')


class CashAllocation(models.Model):
    credit = models.ForeignKey('investments.InvestmentTransaction', on_delete=models.PROTECT, related_name='cash_allocations_out')
    debit = models.ForeignKey('investments.InvestmentTransaction', on_delete=models.PROTECT, related_name='cash_allocations_in')
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['credit', 'debit'], name='unique_cash_allocation'), models.CheckConstraint(condition=models.Q(amount__gt=0), name='cash_allocation_positive')]


class InvestmentHistoryJob(models.Model):
    connection = models.ForeignKey(BankConnection, on_delete=models.PROTECT)
    state = models.CharField(max_length=16, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    lease_until = models.DateTimeField(null=True)
    progress = models.JSONField(default=dict)
    message = models.TextField(blank=True)


class InvestmentCashEvidence(models.Model):
    history = models.JSONField(default=list)
    connection = models.ForeignKey(BankConnection, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=128)
    account_id = models.UUIDField()
    facts = models.JSONField()
    revision = models.PositiveIntegerField(default=1)
    operations = models.ManyToManyField(ReconciledInvestmentOperation, related_name='cash_evidence')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection','external_id'],name='unique_investment_cash_evidence')]


class InvestmentOperationEvent(models.Model):
    event = models.OneToOneField(InvestmentEvent, on_delete=models.PROTECT, related_name='operation_membership')
    operation = models.ForeignKey(ReconciledInvestmentOperation, on_delete=models.PROTECT, related_name='event_memberships')
