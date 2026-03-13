from django.urls import path

from pretix.api.urls import orga_router

from . import views
from .api import OIDCTeamAssignmentRuleViewSet

urlpatterns = [
    path("oidc/callback/", views.oidc_callback, name="oidc_callback"),
    path(
        "control/organizer/<str:organizer>/teams/assignment_rules/",
        views.AssignmentRulesList.as_view(),
        name="team_assignment_rules",
    ),
    path(
        "control/organizer/<str:organizer>/teams/assignment_rules/add",
        views.AssignmentRuleCreate.as_view(),
        name="team_assignment_rules.add",
    ),
    path(
        "control/organizer/<str:organizer>/teams/assignment_rules/<int:pk>/delete",
        views.AssignmentRuleDelete.as_view(),
        name="team_assignment_rules.delete",
    ),
]

orga_router.register(
    "team_assignment_rules",
    OIDCTeamAssignmentRuleViewSet,
    basename="team_assignment_rule",
)

