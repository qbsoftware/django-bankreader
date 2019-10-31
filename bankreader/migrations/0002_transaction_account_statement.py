# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-10-30 23:00
from __future__ import unicode_literals

from bankreader.readers import get_reader_choices
from django.db import migrations, models
import django.db.models.deletion


def set_transaction_account_statement(apps, schema_editor):
    AccountStatement = apps.get_model('bankreader', 'AccountStatement')
    Transaction = apps.get_model('bankreader', 'Transaction')
    for transaction in Transaction.objects.iterator():
        transaction.account_statement = AccountStatement.objects.filter(
            from_date__lte=transaction.accounted_date,
            to_date__gte=transaction.accounted_date,
        ).order_by('id').first()
        if transaction.account_statement:
            transaction.save()
    orphans = Transaction.objects.filter(account_statement=None)
    first, last = orphans.first(), orphans.last()
    if first and last:
        orphans.update(account_statement=AccountStatement.objects.create(
            account_id=transaction.account_id,
            statement='_deleted_',
            from_date=first.accounted_date,
            to_date=last.accounted_date,
        ))


class Migration(migrations.Migration):

    dependencies = [
        ('bankreader', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='accountstatement',
            options={'ordering': ('from_date',), 'verbose_name': 'account statement', 'verbose_name_plural': 'account statements'},
        ),
        migrations.AlterField(
            model_name='accountstatement',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='account_statements', to='bankreader.Account', verbose_name='account'),
        ),
        migrations.AddField(
            model_name='account',
            name='reader',
            field=models.CharField(blank=True, choices=get_reader_choices(), max_length=150, null=True, verbose_name='account statement format'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='account_statement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='bankreader.AccountStatement', verbose_name='account statement'),
        ),
        migrations.RunPython(set_transaction_account_statement),
    ]
