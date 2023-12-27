from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DemoAppConfig(AppConfig):
    name = "bankreader_demo.demoapp"
    verbose_name = _("Bank Reader Demo App")

    def ready(self) -> None:
        # register bank statement readers
        from . import readers  # noqa
