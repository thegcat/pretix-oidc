import pytest
from django_scopes import scopes_disabled
from rest_framework.test import APIClient

from pretix.base.models import Organizer, Team
from pretix_oidc.models import OIDCTeamAssignmentRule


@pytest.fixture
@scopes_disabled()
def organizer():
    return Organizer.objects.create(name="Dummy", slug="dummy")



@pytest.fixture
@scopes_disabled()
def team(organizer):
    return Team.objects.create(
        organizer=organizer,
        name="Test-Team",
        can_change_teams=True,
        can_change_organizer_settings=True,
    )


@pytest.fixture
@scopes_disabled()
def second_team(organizer):
    return Team.objects.create(
        organizer=organizer,
        name="Second-Team",
        can_change_organizer_settings=False,
    )


@pytest.fixture
@scopes_disabled()
def other_organizer():
    return Organizer.objects.create(name="Other", slug="other")


@pytest.fixture
@scopes_disabled()
def other_team(other_organizer):
    return Team.objects.create(
        organizer=other_organizer,
        name="Other-Team",
        can_change_organizer_settings=True,
    )


@pytest.fixture
@scopes_disabled()
def token_client(team):
    client = APIClient()
    t = team.tokens.create(name="Foo")
    client.credentials(HTTP_AUTHORIZATION="Token " + t.token)
    return client


@pytest.fixture
@scopes_disabled()
def no_perm_team(organizer):
    return Team.objects.create(
        organizer=organizer,
        name="NoPerm-Team",
        can_change_organizer_settings=False,
    )


@pytest.fixture
@scopes_disabled()
def no_perm_token_client(no_perm_team):
    client = APIClient()
    t = no_perm_team.tokens.create(name="Bar")
    client.credentials(HTTP_AUTHORIZATION="Token " + t.token)
    return client


@pytest.fixture
@scopes_disabled()
def rule(team):
    return OIDCTeamAssignmentRule.objects.create(
        team=team, attribute="groups", value="admin"
    )


def _url(organizer, pk=None):
    base = f"/api/v1/organizers/{organizer.slug}/team_assignment_rules/"
    if pk is not None:
        return f"{base}{pk}/"
    return base


@pytest.mark.django_db
def test_list_empty(token_client, organizer):
    resp = token_client.get(_url(organizer))
    assert resp.status_code == 200
    assert resp.data["results"] == []


@pytest.mark.django_db
def test_list_with_rules(token_client, organizer, rule):
    resp = token_client.get(_url(organizer))
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["id"] == rule.pk
    assert resp.data["results"][0]["team"] == rule.team_id
    assert resp.data["results"][0]["attribute"] == "groups"
    assert resp.data["results"][0]["value"] == "admin"


@pytest.mark.django_db
def test_detail(token_client, organizer, rule):
    resp = token_client.get(_url(organizer, rule.pk))
    assert resp.status_code == 200
    assert resp.data["id"] == rule.pk
    assert resp.data["team"] == rule.team_id
    assert resp.data["attribute"] == "groups"
    assert resp.data["value"] == "admin"


@pytest.mark.django_db
def test_create(token_client, organizer, team):
    resp = token_client.post(
        _url(organizer),
        {"team": team.pk, "attribute": "roles", "value": "editor"},
        format="json",
    )
    assert resp.status_code == 201
    with scopes_disabled():
        r = OIDCTeamAssignmentRule.objects.get(pk=resp.data["id"])
        assert r.team == team
        assert r.attribute == "roles"
        assert r.value == "editor"


@pytest.mark.django_db
def test_create_with_second_team(token_client, organizer, second_team):
    resp = token_client.post(
        _url(organizer),
        {"team": second_team.pk, "attribute": "department", "value": "sales"},
        format="json",
    )
    assert resp.status_code == 201
    with scopes_disabled():
        r = OIDCTeamAssignmentRule.objects.get(pk=resp.data["id"])
        assert r.team == second_team


@pytest.mark.django_db
def test_create_team_from_other_organizer_rejected(
    token_client, organizer, other_team
):
    resp = token_client.post(
        _url(organizer),
        {"team": other_team.pk, "attribute": "roles", "value": "admin"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_duplicate_rejected(token_client, organizer, rule):
    resp = token_client.post(
        _url(organizer),
        {"team": rule.team_id, "attribute": rule.attribute, "value": rule.value},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_update(token_client, organizer, rule):
    resp = token_client.patch(
        _url(organizer, rule.pk),
        {"value": "superadmin"},
        format="json",
    )
    assert resp.status_code == 200
    rule.refresh_from_db()
    assert rule.value == "superadmin"


@pytest.mark.django_db
def test_update_team(token_client, organizer, rule, second_team):
    resp = token_client.patch(
        _url(organizer, rule.pk),
        {"team": second_team.pk},
        format="json",
    )
    assert resp.status_code == 200
    rule.refresh_from_db()
    assert rule.team == second_team


@pytest.mark.django_db
def test_update_team_other_organizer_rejected(token_client, organizer, rule, other_team):
    resp = token_client.patch(
        _url(organizer, rule.pk),
        {"team": other_team.pk},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_delete(token_client, organizer, rule):
    resp = token_client.delete(_url(organizer, rule.pk))
    assert resp.status_code == 204
    with scopes_disabled():
        assert not OIDCTeamAssignmentRule.objects.filter(pk=rule.pk).exists()


@pytest.mark.django_db
def test_no_permission_list(no_perm_token_client, organizer):
    resp = no_perm_token_client.get(_url(organizer))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_no_permission_create(no_perm_token_client, organizer, team):
    resp = no_perm_token_client.post(
        _url(organizer),
        {"team": team.pk, "attribute": "roles", "value": "admin"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_no_permission_delete(no_perm_token_client, organizer, rule):
    resp = no_perm_token_client.delete(_url(organizer, rule.pk))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_other_organizer_rules_not_visible(token_client, organizer, other_team):
    with scopes_disabled():
        OIDCTeamAssignmentRule.objects.create(
            team=other_team, attribute="groups", value="admin"
        )
    resp = token_client.get(_url(organizer))
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 0


