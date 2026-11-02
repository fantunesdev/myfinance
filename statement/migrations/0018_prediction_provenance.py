from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("statement", "0017_classifier_source_category")]
    operations = [
        migrations.AlterField(
            model_name="transaction", name="original_description", field=models.TextField(blank=True, null=True)
        ),
        migrations.AddField(
            model_name="categorizationfeedback",
            name="original_description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
    for model in ("transaction", "categorizationfeedback"):
        for name, field in (
            ("merchant_description", models.CharField(max_length=255, blank=True, default="")),
            ("source_type", models.CharField(max_length=20, blank=True, default="")),
            ("source_app", models.CharField(max_length=255, blank=True, default="")),
            (
                "event_type",
                models.CharField(
                    max_length=20,
                    blank=True,
                    choices=[
                        ("purchase", "Compra"),
                        ("card_payment", "Pagamento da fatura"),
                        ("refund", "Estorno"),
                        ("unknown", "Revisar evento"),
                    ],
                    default="unknown",
                ),
            ),
            (
                "source_notification",
                models.ForeignKey(
                    "statement.notification",
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True,
                    related_name="+",
                ),
            ),
        ):
            operations.append(migrations.AddField(model_name=model, name=name, field=field))

    for name, target in (
        ("predicted_category_id", "category"),
        ("predicted_subcategory_id", "subcategory"),
        ("corrected_category_id", "category"),
        ("corrected_subcategory_id", "subcategory"),
    ):
        operations.append(
            migrations.AlterField(
                model_name="categorizationfeedback",
                name=name,
                field=models.ForeignKey(
                    "statement." + target,
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True,
                    related_name="+",
                ),
            )
        )
