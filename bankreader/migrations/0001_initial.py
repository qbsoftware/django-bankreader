from django.db import migrations, models
import django.db.models.deletion
import localflavor.generic.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=150, unique=True, verbose_name="account name"),
                ),
                (
                    "iban",
                    localflavor.generic.models.IBANField(
                        blank=True,
                        include_countries=None,
                        max_length=34,
                        null=True,
                        use_nordea_extensions=False,
                        verbose_name="IBAN",
                    ),
                ),
                (
                    "bic",
                    localflavor.generic.models.BICField(
                        blank=True, max_length=11, null=True, verbose_name="BIC (SWIFT)"
                    ),
                ),
            ],
            options={
                "verbose_name": "account",
                "verbose_name_plural": "accounts",
            },
        ),
        migrations.CreateModel(
            name="AccountStatement",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "statement",
                    models.CharField(max_length=256, verbose_name="statement"),
                ),
                (
                    "from_date",
                    models.DateField(editable=False, verbose_name="from date"),
                ),
                ("to_date", models.DateField(editable=False, verbose_name="to date")),
                (
                    "account",
                    models.ForeignKey(
                        limit_choices_to={"reader__isnull": False},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_statements",
                        to="bankreader.Account",
                        verbose_name="account",
                    ),
                ),
            ],
            options={
                "ordering": ("from_date",),
            },
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "transaction_id",
                    models.CharField(max_length=256, verbose_name="transaction id"),
                ),
                ("entry_date", models.DateField(verbose_name="entry date")),
                ("accounted_date", models.DateField(verbose_name="accounted date")),
                (
                    "remote_account_number",
                    models.CharField(max_length=64, verbose_name="remote account number"),
                ),
                (
                    "remote_account_name",
                    models.CharField(max_length=128, verbose_name="remote account name"),
                ),
                (
                    "amount",
                    models.DecimalField(decimal_places=2, max_digits=20, verbose_name="amount"),
                ),
                (
                    "variable_symbol",
                    models.BigIntegerField(default=0, verbose_name="variable symbol"),
                ),
                (
                    "constant_symbol",
                    models.BigIntegerField(default=0, verbose_name="constant symbol"),
                ),
                (
                    "specific_symbol",
                    models.BigIntegerField(default=0, verbose_name="specific symbol"),
                ),
                (
                    "sender_description",
                    models.CharField(max_length=256, verbose_name="description for sender"),
                ),
                (
                    "recipient_description",
                    models.CharField(max_length=256, verbose_name="description for recipient"),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bankreader.Account",
                        verbose_name="account",
                    ),
                ),
            ],
            options={
                "verbose_name": "transaction",
                "verbose_name_plural": "transactions",
                "ordering": ("accounted_date",),
            },
        ),
        migrations.AlterUniqueTogether(
            name="transaction",
            unique_together={("account", "transaction_id")},
        ),
    ]
