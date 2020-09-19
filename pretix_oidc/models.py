from django.db import models
from django.utils.translation import ugettext_lazy as _

from pretix.base.models import Team


class OIDCTeamAssignmentRule(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    attribute = models.CharField(max_length=255, verbose_name=_('OIDC attribute'))
    value = models.CharField(max_length=255, verbose_name=_('Attribute value'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['team', 'attribute', 'value'], name='unique_rule')
        ]
        verbose_name = _('Team assignment rule')
