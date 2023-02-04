from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_oidc"
    verbose_name = "Pretix OIDC"

    class PretixPluginMeta:
        name = gettext_lazy("Pretix OIDC")
        author = "Jaakko Rinta-Filppula, Felix Schäfer"
        description = gettext_lazy("OIDC authentication plugin for Pretix")
        visible = True
        version = __version__
        category = "FEATURE"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


