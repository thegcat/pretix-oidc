from django.utils.translation import gettext_lazy

from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_oidc"
    verbose_name = "pretix OIDC"

    class PretixPluginMeta:
        name = gettext_lazy("pretix OIDC")
        author = "Jaakko Rinta-Filppula, Felix Schäfer"
        description = gettext_lazy("OIDC authentication plugin for pretix")
        visible = False
        version = __version__
        category = "FEATURE"
        compatibility = "pretix>=4.16.0"

    def ready(self):
        from . import signals  # NOQA
