from django.db import models
from django.utils.translation import gettext_lazy
from pretix.base.models import Team, User


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

class OIDCSession(models.Model):
    """
    Persisted mapping between Django sessions and OIDC sessions.

    Augments the Django session with OIDC-specific identifiers
    (issuer, subject, session ID) to enable efficient session lookup and
    cleanup during OIDC back-channel logout.
    """
    # django user id -> lookup by django user id
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # django session id -> lookup by django session
    session_id = models.CharField(max_length=255)
    # django user id -> lookup by user_session_id
    oidc_session_id = models.CharField(max_length=255)
    oidc_user_id = models.CharField(max_length=255)
    oidc_issuer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
