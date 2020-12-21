# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField

from .readers import get_reader_choices, readers


class Account(models.Model):
    name = models.CharField(_('account name'), max_length=150, unique=True)
    iban = IBANField(_('IBAN'), blank=True, null=True)
    bic = BICField(_('BIC (SWIFT)'), blank=True, null=True)
    reader = models.CharField(
        _('account statement format'), blank=True, choices=get_reader_choices(), max_length=150, null=True
    )

    class Meta:
        verbose_name = _('account')
        verbose_name_plural = _('accounts')

    def __str__(self):
        return self.name

    def get_reader(self):
        return readers.get(self.reader)


class AccountStatement(models.Model):
    account = models.ForeignKey(
        Account,
        limit_choices_to={'reader__isnull': False},
        on_delete=models.CASCADE,
        related_name='account_statements',
        verbose_name=_('account'),
    )
    statement = models.CharField(_('statement'), max_length=256)
    from_date = models.DateField(_('from date'), editable=False)
    to_date = models.DateField(_('to date'), editable=False)

    class Meta:
        ordering = ('from_date',)
        verbose_name = _('account statement')
        verbose_name_plural = _('account statements')

    def __str__(self):
        return self.statement


class Transaction(models.Model):
    transaction_id = models.CharField(_('transaction id'), max_length=256)
    account_statement = models.ForeignKey(
        AccountStatement, on_delete=models.CASCADE, related_name='transactions', verbose_name=_('account statement')
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name=_('account'))
    entry_date = models.DateField(_('entry date'))
    accounted_date = models.DateField(_('accounted date'))
    remote_account_number = models.CharField(_('remote account number'), max_length=64)
    remote_account_name = models.CharField(_('remote account name'), max_length=128)
    amount = models.DecimalField(_('amount'), decimal_places=2, max_digits=20)
    variable_symbol = models.BigIntegerField(_('variable symbol'), default=0)
    constant_symbol = models.BigIntegerField(_('constant symbol'), default=0)
    specific_symbol = models.BigIntegerField(_('specific symbol'), default=0)
    sender_description = models.CharField(_('description for sender'), max_length=256)
    recipient_description = models.CharField(_('description for recipient'), max_length=256)

    class Meta:
        ordering = ('accounted_date',)
        unique_together = ('account', 'transaction_id')
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
