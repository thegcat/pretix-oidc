from .oidc_connector import OIDCAuthBackend # NOQA

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from pretix.base.models import Organizer, Team, User
from pretix.control.views.auth import process_login


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

    organizer = Organizer.objects.get(slug=auth_backend.organizer)
    team = organizer.teams.first()
    team.members.add(user)

    return process_login(request, user, False)
