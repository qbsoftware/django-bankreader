import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bankreader", "0002_transaction_account_statement"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="account_statement",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="transactions",
                to="bankreader.AccountStatement",
                verbose_name="account statement",
            ),
        ),
    ]
