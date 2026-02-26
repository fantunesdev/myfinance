from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statement', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='prepaid',
            field=models.BooleanField(default=False),
        ),
    ]
