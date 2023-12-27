# -*- coding: utf-8 -*-

from typing import Any

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from bankreader.models import Transaction


class Order(models.Model):
    name = models.CharField(max_length=30)
    variable_symbol = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")

    def __str__(self) -> str:
        return self.name


class OrderPayment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    transaction = models.OneToOneField(
        Transaction,
        editable=False,
        null=True,
        on_delete=models.CASCADE,
        related_name="identified_order_payment",
    )
    amount = models.DecimalField(_("amount"), decimal_places=2, max_digits=20)

    class Meta:
        verbose_name = _("order payment")
        verbose_name_plural = _("order payments")

    def __str__(self) -> str:
        return "{}, {}".format(self.order, self.amount)


@receiver(post_save, sender=Transaction)
def create_order_payment(instance: Transaction, **kwargs: Any) -> None:
    transaction = instance
    order = Order.objects.filter(variable_symbol=transaction.variable_symbol).first()
    if order:
        OrderPayment.objects.create(order=order, transaction=transaction, amount=transaction.amount)
