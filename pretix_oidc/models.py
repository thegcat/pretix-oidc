from django.db import models
from django.utils.translation import gettext_lazy
from pretix.base.models import Team


class OIDCTeamAssignmentRule(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    attribute = models.CharField(
        max_length=255, verbose_name=gettext_lazy("OIDC attribute")
    )
    value = models.CharField(
        max_length=255, verbose_name=gettext_lazy("Attribute value")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "attribute", "value"], name="unique_rule"
            )
        ]
        verbose_name = gettext_lazy("Team assignment rule")
