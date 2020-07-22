from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from pretix.control.permissions import organizer_permission_required
from pretix.control.signals import nav_organizer


@organizer_permission_required('can_change_organizer_settings')
@receiver(nav_organizer)
def add_team_auto_assign_to_nav_pane(sender, request, **kwargs):
    """
    This signal is used to add the 'Team assignment rules' column to the navigation pane.
    """
    return [
        {
            'label': _('Team assignment rules'),
            'url': reverse(
                'plugins:pretix_oidc:team_assignment_rules',
                kwargs={
                    'organizer': request.organizer.slug
                }
            ),
            'active': (request.resolver_match.url_name.startswith('team_assignment_rules')),
            'icon': 'group',
        },
    ]
