# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import django
from django import forms
from django.contrib import admin
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.urls import reverse_lazy as reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from .models import Account, AccountStatement, Transaction
from .readers import get_reader_choices, readers

logger = logging.getLogger(__name__)


class AmountFieldListFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_credit = '%s__gt' % field_path
        self.lookup_kwarg_debit = '%s__lt' % field_path
        self.lookup_val_credit = params.get(self.lookup_kwarg_credit)
        self.lookup_val_debit = params.get(self.lookup_kwarg_debit)
        super(AmountFieldListFilter, self).__init__(field, request, params, model, model_admin, field_path)

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
    list_display = ('name', 'iban', 'bic')


class AccountNamePlusReadOnlyMixin:
    # account name
    def get_queryset(self, request):
        return super(AccountNamePlusReadOnlyMixin, self).get_queryset(request).select_related('account')

    def account_name(self, obj):
        return obj.account.name
    account_name.short_description = _('account')
    account_name.admin_order_field = 'account__name'

    # read only
    if django.VERSION > (2,):
        def has_change_permission(self, request, obj=None):
            return False
    else:
        def get_readonly_fields(self, request, obj=None):
            return tuple(
                f.name for f in self.model._meta.fields
                if not f.primary_key
            ) if obj else ()


@admin.register(AccountStatement)
class AccountStatementAdmin(AccountNamePlusReadOnlyMixin, admin.ModelAdmin):
    list_display = ('statement', 'account_name', 'from_date', 'to_date')
    list_filter = ('account',)

    class form(forms.ModelForm):
        statement = forms.FileField(label=_('account statement'))
        reader = forms.ChoiceField(label=_('file format'), choices=get_reader_choices())

        def clean(self):
            if self.cleaned_data.get('reader') and self.cleaned_data.get('statement'):
                reader = readers[self.cleaned_data['reader']]
                try:
                    self.transactions_data = tuple(reader.read_archive(self.cleaned_data['statement'].file))
                except Exception as e:
                    msg = _('Failed to read transaction data in format {}.').format(reader.label)
                    logger.exception(msg)
                    raise ValidationError(msg)
                if not self.transactions_data:
                    raise ValidationError(_('The account statement doesn\'t contain any transaction data.'))
                self.instance.from_date = min(td['accounted_date'] for td in self.transactions_data)
                self.instance.to_date = max(td['accounted_date'] for td in self.transactions_data)

        def save(self, commit=True):
            with transaction.atomic():
                instance = super(AccountStatementAdmin.form, self).save(commit)
                for transaction_data in self.transactions_data:
                    try:
                        with transaction.atomic():
                            Transaction.objects.create(account=self.instance.account, **transaction_data)
                    except IntegrityError:
                        pass
            return instance


@admin.register(Transaction)
class TransactionAdmin(AccountNamePlusReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = 'accounted_date'
    list_display = tuple(
        ('account_name' if f.name == 'account' else f.name) for f in Transaction._meta.fields
    )[1:] + tuple(
        r.name + '_link' for r in Transaction._meta.related_objects
    )
    list_filter = ('account', ('amount', AmountFieldListFilter)) + tuple(
        (r.name, IdentifiedFieldListFilter)
        for r in Transaction._meta.related_objects
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for related_object in Transaction._meta.related_objects:
            changelist_url = reverse('admin:{}_{}_changelist'.format(
                related_object.related_model._meta.app_label,
                related_object.related_model._meta.model_name,
            ))
            add_url = reverse('admin:{}_{}_add'.format(
                related_object.related_model._meta.app_label,
                related_object.related_model._meta.model_name,
            ))

            def related_object_link(obj):
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
                        '<a href="{add_url}?{remote_name}={obj_id}" title="{title}">'
                        '<img src="{icon}" alt="+"/></a>',
                        add_url=add_url,
                        remote_name=related_object.remote_field.name,
                        obj_id=obj.id,
                        title=_('add'),
                        icon=static('admin/img/icon-addlink.svg'),
                    )
            related_object_link.allow_tags = True
            related_object_link.short_description = related_object.related_model._meta.verbose_name
        setattr(self, related_object.name + '_link', related_object_link)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        for related_object in Transaction._meta.related_objects:
            qs = qs.select_related(related_object.name)
        return qs

    def has_add_permission(self, request):
        return False
