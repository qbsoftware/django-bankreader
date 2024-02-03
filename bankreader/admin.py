import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, List, Tuple, Type

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.db.models.fields.reverse_related import OneToOneRel
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse_lazy as reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from bankreader.readers import get_reader_choices

from .models import Account, AccountStatement, Transaction

logger = logging.getLogger(__name__)


if TYPE_CHECKING:

    class AccountWithStatementsCount(Account):
        account_statements_count: int

    class AccountStatementWithTransactionsCount(AccountStatement):
        transactions_count: int


def get_transaction_relations() -> Dict[str, OneToOneRel]:
    return {rel.name: rel for rel in Transaction._meta.related_objects if isinstance(rel, OneToOneRel)}  # type: ignore


class AmountFieldListFilter(admin.FieldListFilter):
    def __init__(
        self,
        field: models.Field,
        request: HttpRequest,
        params: Dict[str, str],
        model: Type[models.Model],
        model_admin: admin.ModelAdmin,
        field_path: str,
    ) -> None:
        self.lookup_kwarg_credit = "%s__gt" % field_path
        self.lookup_kwarg_debit = "%s__lt" % field_path
        self.lookup_val_credit = params.get(self.lookup_kwarg_credit)
        self.lookup_val_debit = params.get(self.lookup_kwarg_debit)
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self) -> list[str | None]:
        return [self.lookup_kwarg_credit, self.lookup_kwarg_debit]

    def choices(self, changelist: ChangeList) -> Generator[dict[str, Any], None, None]:
        yield {
            "selected": self.lookup_val_credit is None and self.lookup_val_debit is None,
            "query_string": changelist.get_query_string(remove=[self.lookup_kwarg_credit, self.lookup_kwarg_debit]),
            "display": _("All"),
        }
        yield {
            "selected": self.lookup_val_credit == "0",
            "query_string": changelist.get_query_string({self.lookup_kwarg_credit: "0"}, [self.lookup_kwarg_debit]),
            "display": _("Credit transactions"),
        }
        yield {
            "selected": self.lookup_val_debit == "0",
            "query_string": changelist.get_query_string({self.lookup_kwarg_debit: "0"}, [self.lookup_kwarg_credit]),
            "display": _("Debit transactions"),
        }


class IdentifiedFieldListFilter(admin.RelatedFieldListFilter):
    def choices(self, changelist: ChangeList) -> Generator[dict[str, Any], None, None]:
        yield {
            "selected": self.lookup_val_isnull is None,
            "query_string": changelist.get_query_string(remove=[self.lookup_kwarg_isnull]),
            "display": _("All"),
        }
        yield {
            "selected": self.lookup_val_isnull == "True",
            "query_string": changelist.get_query_string({self.lookup_kwarg_isnull: "True"}),
            "display": _("Not identified"),
        }
        yield {
            "selected": self.lookup_val_isnull == "False",
            "query_string": changelist.get_query_string({self.lookup_kwarg_isnull: "False"}),
            "display": _("Identified"),
        }


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "iban", "bic", "account_statements_link")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet["AccountWithStatementsCount"]:
        return super().get_queryset(request).annotate(account_statements_count=models.Count("account_statements"))

    account_statement_changelist = reverse("admin:bankreader_accountstatement_changelist")

    @admin.display(description=_("account statements"), ordering="account_statements_count")
    def account_statements_link(self, obj: "AccountWithStatementsCount") -> str:
        return mark_safe(
            '<a href="{url}?account__id__exact={account_id}">{count}</a>'.format(
                url=self.account_statement_changelist,
                account_id=obj.id,
                count=obj.account_statements_count,
            )
        )

    def formfield_for_dbfield(self, db_field: models.Field, request: HttpRequest, **kwargs: Any) -> forms.Field | None:
        if db_field.name == "reader":
            return forms.ChoiceField(choices=get_reader_choices())
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class ReadOnlyMixin:
    def has_change_permission(self, request: HttpRequest, obj: models.Model | None = None) -> bool:
        return False


class AccountStatementForm(forms.ModelForm):
    statement = forms.FileField(label=_("account statement"))
    transactions: tuple[Transaction, ...] | None = None

    def clean(self) -> dict[str, Any]:
        account: Account | None = self.cleaned_data.get("account")
        statement: UploadedFile | None = self.cleaned_data.get("statement")
        if account is None or statement is None or statement.file is None:
            return self.cleaned_data
        reader = account.get_reader()
        assert reader is not None
        try:
            self.transactions = tuple(reader.read_file(statement.file))
        except Exception:
            msg = _("Failed to read transaction data in format {}.").format(reader.label)
            logger.exception(msg)
            raise ValidationError(msg)
        if not self.transactions:
            raise ValidationError(_("The account statement doesn't contain any transaction data."))
        return self.cleaned_data


@admin.register(AccountStatement)
class AccountStatementAdmin(ReadOnlyMixin, admin.ModelAdmin):
    form = AccountStatementForm
    list_display = (
        "id",
        "statement",
        "account_name",
        "from_date",
        "to_date",
        "transactions_link",
    )
    list_filter = ("account",)
    ordering = ("-to_date",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet["AccountStatementWithTransactionsCount"]:
        return (
            super()
            .get_queryset(request)
            .select_related("account")
            .annotate(transactions_count=models.Count("transactions"))
        )

    @admin.display(description=_("account"), ordering="account__name")
    def account_name(self, obj: AccountStatement) -> str:
        return obj.account.name

    transaction_changelist = reverse("admin:bankreader_transaction_changelist")

    @admin.display(description=_("transactions"), ordering="transactions_count")
    def transactions_link(self, obj: "AccountStatementWithTransactionsCount") -> str:
        return mark_safe(
            '<a href="{url}?account_statement__id__exact={account_statement_id}">{count}</a>'.format(
                url=self.transaction_changelist,
                account_statement_id=obj.id,
                count=obj.transactions_count,
            )
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: AccountStatement,
        form: AccountStatementForm,
        change: bool,
    ) -> None:
        assert form.transactions is not None
        for message in obj.save_with_transactions(form.transactions):
            messages.warning(request, message)
        messages.success(request, _("Account statement was successfully loaded."))


@admin.register(Transaction)
class TransactionAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "accounted_date"
    ordering = ("-accounted_date",)
    list_filter = [
        "account_statement__account",
        ("amount", AmountFieldListFilter),
    ]

    def get_list_display(self, request: HttpRequest) -> List[str | Callable[[Transaction], str]]:  # type: ignore
        return list(self.get_list_display_generator(request))

    def get_list_display_generator(
        self, request: HttpRequest
    ) -> Generator[str | Callable[[Transaction], str], None, None]:
        for field in Transaction._meta.fields[1:]:
            yield field.name

        for relation in get_transaction_relations().values():
            assert isinstance(relation.related_model, type(models.Model))
            RelatedModel: type[models.Model] = relation.related_model

            can_add = request.user.has_perm(f"{RelatedModel._meta.app_label}.add_{RelatedModel._meta.model_name}")
            can_see = request.user.has_perm(f"{RelatedModel._meta.app_label}.view_{RelatedModel._meta.model_name}")

            changelist_url = (
                reverse(
                    "admin:{}_{}_changelist".format(
                        RelatedModel._meta.app_label,
                        RelatedModel._meta.model_name,
                    )
                )
                if can_see
                else ""
            )

            add_url = (
                reverse(
                    "admin:{}_{}_add".format(
                        RelatedModel._meta.app_label,
                        RelatedModel._meta.model_name,
                    )
                )
                if can_add
                else ""
            )

            @admin.display(description=RelatedModel._meta.verbose_name)
            def related_object_link(obj: Transaction) -> str:
                try:
                    related_object = getattr(obj, relation.name)
                except RelatedModel.DoesNotExist:  # type: ignore
                    related_object = None
                if related_object:
                    return (
                        format_html(
                            '<a href="{changelist_url}?{remote_name}__id__exact={obj_id}">{text}</a>',
                            changelist_url=changelist_url,
                            remote_name=relation.remote_field.name,
                            obj_id=obj.id,
                            text=str(related_object),
                        )
                        if can_see
                        else str(related_object)
                    )
                elif can_add:
                    return format_html(
                        '<a href="{add_url}?{remote_name}={obj_id}" title="{title}">' '<img src="{icon}" alt="+"/></a>',
                        add_url=add_url,
                        remote_name=relation.remote_field.name,
                        obj_id=obj.id,
                        title=_("add"),
                        icon=static("admin/img/icon-addlink.svg"),
                    )
                return "-"

            yield related_object_link

    def get_list_filter(  # type: ignore
        self,
        request: HttpRequest,
    ) -> List[Any]:
        return self.list_filter + [(name, IdentifiedFieldListFilter) for name in get_transaction_relations()]

    def get_queryset(self, request: HttpRequest) -> models.QuerySet[Transaction]:
        return (
            super()
            .get_queryset(request)
            .select_related(
                "account",
                "account_statement",
                *(name for name in get_transaction_relations()),
            )
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(description=_("account statement"), ordering="account_statement__statement")
    def statement(self, obj: Transaction) -> str:
        return obj.account_statement.statement
