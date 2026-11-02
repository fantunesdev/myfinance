from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('statement', '0016_classifier_job')]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='source_category',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='categorizationfeedback',
            name='source_category',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
