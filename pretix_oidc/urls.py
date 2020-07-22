from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^oidc/callback/', views.oidc_callback, name='oidc_callback'),
    url(r'^control/organizer/(?P<organizer>[^/]+)/teams/assignment_rules$', views.AssignmentRulesList.as_view(),
        name='team_assignment_rules'),
]
