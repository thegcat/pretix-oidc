from dictlib import dig_get
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from pretix.base.models import Team, User
from pretix.base.models.auth import EmailAddressTakenError
from pretix.control.permissions import OrganizerPermissionRequiredMixin
from pretix.control.views.auth import process_login
from pretix.helpers.compat import CompatDeleteView
from pretix.settings import config

from .auth import OIDCAuthBackend  # NOQA
from .forms import OIDCAssignmentRuleForm
from .models import OIDCTeamAssignmentRule


def oidc_callback(request):
    auth_backend = OIDCAuthBackend()
    user_data, id_token = auth_backend.process_callback(request)

    if user_data is None:
        return redirect("auth.login")

    try:
        user = User.objects.get_or_create_for_backend(
            auth_backend.identifier,
            user_data["uuid"],
            user_data["email"],
            set_always={"fullname": user_data["fullname"]},
            set_on_creation={},
        )
    except EmailAddressTakenError:
        messages.error(
            request,
            _(
                "We cannot create your user account as a user account in this system "
                "already exists with the same email address."
            ),
        )
        return redirect(reverse("control:auth.login"))
    else:
        _add_user_to_teams(user, id_token)
        _add_user_to_staff(user, id_token)
        return process_login(request, user, False)


def _add_user_to_teams(user, id_token):
    rules = OIDCTeamAssignmentRule.objects.all()

    for rule in rules:
        values = _get_attr(id_token, rule.attribute)

        if rule.value in values:
            try:
                rule.team.members.add(user)
            except ObjectDoesNotExist:
                pass
        else:
            rule.team.members.remove(user)


def _add_user_to_staff(user, id_token):
    if config.has_option("oidc", "staff_scope") and config.has_option(
        "oidc", "staff_value"
    ):
        staff_scope = config.get("oidc", "staff_scope")
        staff_values = [v.strip() for v in config.get("oidc", "staff_value").split(",")]
        if staff_scope is not None and staff_values is not None:
            values = _get_attr(id_token, staff_scope)

            user.is_staff = len(set(values) & set(staff_values)) > 0
            user.save()


def _get_attr(id_token, attr_name):
    values = dig_get(id_token, attr_name, [])
    if type(values) is not list:
        values = [values]
    return values


# These views have been adapted from pretix-cas plugin (https://github.com/DataManagementLab/pretix-cas)
class AssignmentRulesList(TemplateView, OrganizerPermissionRequiredMixin):
    template_name = "pretix_oidc/oidc_assignment_rules.html"
    permission = "can_change_organizer_settings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.request.organizer
        context["teams"] = Team.objects.filter(organizer=organizer)
        context["assignmentRules"] = OIDCTeamAssignmentRule.objects.filter(
            team__organizer=organizer
        )
        return context


class AssignmentRuleEditMixin(OrganizerPermissionRequiredMixin):
    model = OIDCTeamAssignmentRule
    permission = "can_change_organizer_settings"

    def get_success_url(self):
        return reverse(
            "plugins:pretix_oidc:team_assignment_rules",
            kwargs={"organizer": self.request.organizer.slug},
        )


class AssignmentRuleUpdateMixin(AssignmentRuleEditMixin):
    fields = ["team", "attribute"]
    template_name = "pretix_oidc/oidc_assignment_rule_edit.html"

    def get_form(self, form_class=None):
        return OIDCAssignmentRuleForm(
            organizer=self.request.organizer, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        super().form_valid(form)
        messages.success(self.request, _("The new assignment rule has been created."))
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, _("The assignment rule could not be created."))
        return super().form_invalid(form)


class AssignmentRuleCreate(AssignmentRuleUpdateMixin, CreateView):
    pass


class AssignmentRuleDelete(AssignmentRuleEditMixin, CompatDeleteView):
    template_name = "pretix_oidc/oidc_assignment_rule_delete.html"
