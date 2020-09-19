from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^oidc/callback/', views.oidc_callback, name='oidc_callback'),
    url(r'^control/organizer/(?P<organizer>[^/]+)/teams/assignment_rules$',
        views.AssignmentRulesList.as_view(),
        name='team_assignment_rules'),
    url(r'^control/organizer/(?P<organizer>[^/]+)/teams/assignment_rules/add$',
        views.AssignmentRuleCreate.as_view(),
        name='team_assignment_rules.add'),
    url(r'^control/organizer/(?P<organizer>[^/]+)/teams/assignment_rules/(?P<pk>\d+)/delete$',
        views.AssignmentRuleDelete.as_view(),
        name='team_assignment_rules.delete'),
]
