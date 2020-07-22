from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from pretix.base.models import Organizer, Team, User
from pretix.control.permissions import OrganizerPermissionRequiredMixin
from pretix.control.views.auth import process_login

from .forms import OIDCAssignmentRuleForm
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


# These views have been adapted from pretix-cas plugin (https://github.com/DataManagementLab/pretix-cas)
class AssignmentRulesList(TemplateView, OrganizerPermissionRequiredMixin):
    template_name = 'pretix_oidc/oidc_assignment_rules.html'
    permission = 'can_change_organizer_settings'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.request.organizer
        context['teams'] = Team.objects.filter(organizer=organizer)
        context['assignmentRules'] = OIDCTeamAssignmentRule.objects.filter(team__organizer=organizer)
        return context


class AssignmentRuleEditMixin(OrganizerPermissionRequiredMixin):
    model = OIDCTeamAssignmentRule
    permission = 'can_change_organizer_settings'

    def get_success_url(self):
        return reverse('plugins:pretix_oidc:team_assignment_rules',
                       kwargs={'organizer': self.request.organizer.slug})


class AssignmentRuleUpdateMixin(AssignmentRuleEditMixin):
    fields = ['team', 'attribute']
    template_name = 'pretix_oidc/oidc_assignment_rule_edit.html'

    def get_form(self, form_class=None):
        return OIDCAssignmentRuleForm(organizer=self.request.organizer, **self.get_form_kwargs())

    def form_valid(self, form):
        super().form_valid(form)
        messages.success(self.request, _('The new assignment rule has been created.'))
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, _('The assignment rule could not be created.'))
        return super().form_invalid(form)


class AssignmentRuleCreate(AssignmentRuleUpdateMixin, CreateView):
    pass
