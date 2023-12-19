# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import django
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError
from django.templatetags.static import static
from django.urls import reverse_lazy as reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .models import Account, AccountStatement, Transaction

logger = logging.getLogger(__name__)


class AmountFieldListFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_credit = '%s__gt' % field_path
        self.lookup_kwarg_debit = '%s__lt' % field_path
        self.lookup_val_credit = params.get(self.lookup_kwarg_credit)
        self.lookup_val_debit = params.get(self.lookup_kwarg_debit)
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg_credit, self.lookup_kwarg_debit]

    def choices(self, changelist):
        yield {
            'selected': self.lookup_val_credit is None and self.lookup_val_debit is None,
            'query_string': changelist.get_query_string(remove=[self.lookup_kwarg_credit, self.lookup_kwarg_debit]),
            'display': _('All'),
        }
        yield {
            'selected': self.lookup_val_credit == '0',
            'query_string': changelist.get_query_string({self.lookup_kwarg_credit: '0'}, [self.lookup_kwarg_debit]),
            'display': _('Credit transactions'),
        }
        yield {
            'selected': self.lookup_val_debit == '0',
            'query_string': changelist.get_query_string({self.lookup_kwarg_debit: '0'}, [self.lookup_kwarg_credit]),
            'display': _('Debit transactions'),
        }


class IdentifiedFieldListFilter(admin.RelatedFieldListFilter):
    def choices(self, changelist):
        yield {
            'selected': self.lookup_val_isnull is None,
            'query_string': changelist.get_query_string(remove=[self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        yield {
            'selected': self.lookup_val_isnull == 'True',
            'query_string': changelist.get_query_string({self.lookup_kwarg_isnull: 'True'}),
            'display': _('Not identified'),
        }
        yield {
            'selected': self.lookup_val_isnull == 'False',
            'query_string': changelist.get_query_string({self.lookup_kwarg_isnull: 'False'}),
            'display': _('Identified'),
        }


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'iban', 'bic', 'account_statements_link')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(account_statements_count=Count('account_statements'))

    account_statement_changelist = reverse('admin:bankreader_accountstatement_changelist')

    @admin.display(description=_('account statements'), ordering='account_statements_count')
    def account_statements_link(self, obj):
        return mark_safe(
            '<a href="{url}?account__id__exact={account_id}">{count}</a>'.format(
                url=self.account_statement_changelist,
                account_id=obj.id,
                count=obj.account_statements_count,
            )
        )


class ReadOnlyMixin:
    # read only
    if django.VERSION > (2,):

        def has_change_permission(self, request, obj=None):
            return False

    else:

        def get_readonly_fields(self, request, obj=None):
            return tuple(f.name for f in self.model._meta.fields if not f.primary_key) if obj else ()


@admin.register(AccountStatement)
class AccountStatementAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ('id', 'statement', 'account_name', 'from_date', 'to_date', 'transactions_link')
    list_filter = ('account',)

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related('account').annotate(transactions_count=Count('transactions'))
        )

    @admin.display(description=_('account'), ordering='account__name')
    def account_name(self, obj):
        return obj.account.name

    transaction_changelist = reverse('admin:bankreader_transaction_changelist')

    @admin.display(description=_('transactions'), ordering='transactions_count')
    def transactions_link(self, obj):
        return mark_safe(
            '<a href="{url}?account_statement__id__exact={account_statement_id}">{count}</a>'.format(
                url=self.transaction_changelist,
                account_statement_id=obj.id,
                count=obj.transactions_count,
            )
        )

    class form(forms.ModelForm):
        statement = forms.FileField(label=_('account statement'))

        def clean(self):
            account = self.cleaned_data.get('account')
            statement = self.cleaned_data.get('statement')
            if account and account.reader and statement:
                reader = account.get_reader()
                try:
                    self.transactions_data = tuple(reader.read_archive(statement.file))
                except Exception:
                    msg = _('Failed to read transaction data in format {}.').format(reader.label)
                    logger.exception(msg)
                    raise ValidationError(msg)
                if not self.transactions_data:
                    raise ValidationError(_('The account statement doesn\'t contain any transaction data.'))
                self.instance.from_date = min(td['accounted_date'] for td in self.transactions_data)
                self.instance.to_date = max(td['accounted_date'] for td in self.transactions_data)

        def save(self, commit=True):
            if hasattr(self, 'transactions_data'):
                with transaction.atomic():
                    instance = super().save(commit)
                    instance.save()
                    for transaction_data in self.transactions_data:
                        try:
                            with transaction.atomic():
                                Transaction.objects.create(
                                    account=instance.account, account_statement=instance, **transaction_data
                                )
                        except IntegrityError:
                            pass
                return instance
            else:
                return super().save(commit)


class TransactionBaseAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = 'accounted_date'
    list_display = tuple(('statement' if f.name == 'account_statement' else f.name) for f in Transaction._meta.fields)[
        1:
    ] + tuple(r.name + '_link' for r in Transaction._meta.related_objects)
    list_filter = ('account_statement__account', ('amount', AmountFieldListFilter)) + tuple(
        (r.name, IdentifiedFieldListFilter) for r in Transaction._meta.related_objects
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('account', 'account_statement')
        for related_object in Transaction._meta.related_objects:
            qs = qs.select_related(related_object.name)
        return qs

    @admin.display(description=_('account statement'), ordering='account_statement__statement')
    def statement(self, obj):
        return obj.account_statement.statement

    def has_add_permission(self, request):
        return False


def _get_related_object_link(related_object):
    changelist_url = reverse(
        'admin:{}_{}_changelist'.format(
            related_object.related_model._meta.app_label,
            related_object.related_model._meta.model_name,
        )
    )
    add_url = reverse(
        'admin:{}_{}_add'.format(
            related_object.related_model._meta.app_label,
            related_object.related_model._meta.model_name,
        )
    )

    @admin.display(description=related_object.related_model._meta.verbose_name)
    def related_object_link(self, obj):
        try:
            related_obj = getattr(obj, related_object.name)
        except related_object.related_model.DoesNotExist:
            related_obj = None
        if related_obj:
            return format_html(
                '<a href="{changelist_url}?{remote_name}__id__exact={obj_id}">{text}</a>',
                changelist_url=changelist_url,
                remote_name=related_object.remote_field.name,
                obj_id=obj.id,
                text=getattr(obj, related_object.name),
            )
        else:
            return format_html(
                '<a href="{add_url}?{remote_name}={obj_id}" title="{title}">' '<img src="{icon}" alt="+"/></a>',
                add_url=add_url,
                remote_name=related_object.remote_field.name,
                obj_id=obj.id,
                title=_('add'),
                icon=static('admin/img/icon-addlink.svg'),
            )

    return related_object_link


TransactionAdmin = admin.register(Transaction)(
    type(
        "TransactionAdmin",
        (TransactionBaseAdmin,),
        {
            related_object.name + '_link': _get_related_object_link(related_object)
            for related_object in Transaction._meta.related_objects
        },
    )
)
