from django.contrib import admin

from .models import Order, OrderPayment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "variable_symbol",
    )


@admin.register(OrderPayment)
class OrderPaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "transaction", "amount")
