from django.urls import path

from . import views

urlpatterns = [
    path("oidc/callback/", views.oidc_callback, name="oidc_callback"),
    path("oidc/backchannel_logout/", views.oidc_backchannel_logout, name="oidc_backchannel_logout"),
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
