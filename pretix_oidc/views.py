from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.generic import TemplateView

from pretix.base.models import Organizer, Team, User
from pretix.control.permissions import OrganizerPermissionRequiredMixin
from pretix.control.views.auth import process_login

from .models import OIDCTeamAssignmentRule
from .oidc_connector import OIDCAuthBackend # NOQA


def oidc_callback(request):
    auth_backend = OIDCAuthBackend()
    user_data = auth_backend.process_callback(request)

    if user_data is None:
        return redirect('auth.login')

    try:
        user = User.objects.get(email=user_data['email'])
    except User.DoesNotExist:
        user = User(
            email=user_data['email'],
            auth_backend=auth_backend.identifier
        )

    user.fullname = user_data['fullname']
    user.save()

    return process_login(request, user, False)


class AssignmentRulesList(TemplateView, OrganizerPermissionRequiredMixin):
    template_name = 'pretix_oidc/oidc_assignment_rules.html'
    permission = 'can_change_organizer_settings'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.request.organizer
        context['teams'] = Team.objects.filter(organizer=organizer)
        context['assignmentRules'] = OIDCTeamAssignmentRule.objects.filter(team__organizer=organizer)
        return context
