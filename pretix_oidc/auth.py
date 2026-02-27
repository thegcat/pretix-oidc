import logging
import time
from configparser import NoOptionError, NoSectionError
from typing import Optional

from django.urls import reverse
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from django.contrib.sessions.models import Session
from oic import rndstr
from oic.oic import Client
from oic.oic.message import (
    AuthorizationResponse,
    ProviderConfigurationResponse,
    RegistrationResponse,
    BackChannelLogoutRequest,
)
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic.utils.keyio import KeyJar
from pretix.base.auth import BaseAuthBackend
from pretix.settings import config
from django.core.cache import cache

from .models import OIDCSession

CACHE_KEY = 'pretix_oidc_store'

logger = logging.getLogger(__name__)

backchannel_logout_enabled = config.get("oidc", "backchannel_logout", fallback=False)

class OIDCAuthBackend(BaseAuthBackend):
    def __init__(self, op_info: Optional[ProviderConfigurationResponse] = None, client_reg: Optional[RegistrationResponse] = None):
        try:
            self.title = config.get(
                "oidc", "title", fallback="Login with OpenID connect"
            )

            if op_info is None or client_reg is None:
                # setting config.get to None and ProviderConfigurationResponse handles empty string as unset we can use this
                # object as override values
                op_info = ProviderConfigurationResponse(
                    version="1.0",
                    issuer=config.get("oidc", "issuer"),
                    authorization_endpoint=config.get("oidc", "authorization_endpoint", fallback=""),
                    token_endpoint=config.get("oidc", "token_endpoint", fallback=""),
                    userinfo_endpoint=config.get("oidc", "userinfo_endpoint", fallback=""),
                    end_session_endpoint=config.get("oidc", "end_session_endpoint", fallback=""),
                    jwks_uri=config.get("oidc", "jwks_uri", fallback=""),
                )

                client_reg = RegistrationResponse(
                    client_id=config.get("oidc", "client_id"),
                    client_secret=config.get("oidc", "client_secret"),
                )

            self.op_info, self.client_reg = op_info, client_reg

            self.client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
            if not config.get("oidc", "skip_provider_discovery", fallback=False):
                # If skip_provider_discovery is set, we do not fetch the provider config
                # but use the provided information directly.
                self.client.provider_config(self.op_info["issuer"])
            self.client.handle_provider_config(self.op_info, self.op_info["issuer"])

            missing_endpoints = {
                "authorization_endpoint",
                "token_endpoint",
                "userinfo_endpoint",
                "end_session_endpoint"
            } - {
                k
                for k,v
                in self.client.__dict__.items()
                if k.endswith("_endpoint") and v is not None
            }
            if len(missing_endpoints)>0:
                logger.error("Please specify " + ", ".join(sorted(missing_endpoints)) + " in [oidc] section in pretix.cfg")
            # check whether we have at least one key for the issuer
            if  len(self.client.keyjar.get_issuer_keys(self.client.issuer)) == 0:
                logger.error(
                    "Please specify jwks_uri in [oidc] section in pretix.cfg or ensure that the issuer supports jwks_uri discovery."
                )
            self.client.store_registration_info(self.client_reg)
            self.client.redirect_uris = [None]

            self.scopes = config.get("oidc", "scopes", fallback="openid").split(",")
        except (NoSectionError, NoOptionError):
            logger.error(
                "Please specify issuer, client_id and client_secret in [oidc] section in pretix.cfg"
            )

    @property
    def identifier(self):
        return "pretix_oidc"

    @property
    def verbose_name(self):
        return self.title

    def authentication_url(self, request):
        oidc_state = rndstr()
        request.session["oidc_state"] = {
            oidc_state: {
                "next": request.GET.get("next", None),
                "generated_on": int(time.time()),
            }
        }

        auth_req = self.client.construct_AuthorizationRequest(
            request_args={
                "client_id": self.client.client_id,
                "response_type": "code",
                "scope": self.scopes,
                "redirect_uri": self.redirect_uri(request),
                "state": oidc_state,
            }
        )

        return auth_req.request(self.client.authorization_endpoint)

    def redirect_uri(self, request):
        return request.build_absolute_uri(reverse("plugins:pretix_oidc:oidc_callback"))

    def get_next_url(self, request):
        return request.session.pop("oidc_next_url", None)

    def process_callback(self, request):
        auth_response = self.client.parse_response(
            AuthorizationResponse,
            info=request.META["QUERY_STRING"],
            sformat="urlencoded",
        )

        request.session["oidc_next_url"] = None
        oidc_state = request.session.pop("oidc_state", None)
        response_state = auth_response.get("state", None)

        if not oidc_state or not response_state:
            return [None, None]

        if response_state not in oidc_state:
            return [None, None]

        if oidc_state[response_state]["generated_on"] < time.time() - 5 * 60:
            return [None, None]

        request.session["oidc_next_url"] = oidc_state[response_state]["next"]

        access_token_response = self.client.do_access_token_request(
            state=auth_response["state"],
            scope=self.scopes,
            request_args={
                "code": auth_response["code"],
                "redirect_uri": self.redirect_uri(request),
            },
            authn_method="client_secret_basic",
        )

        userinfo = self.client.do_user_info_request(state=auth_response["state"])

        id_token = access_token_response["id_token"]
        user_data = {
            "uuid": userinfo[config.get("oidc", "unique_attribute", fallback="sub")],
            "email": userinfo["email"],
            "fullname": userinfo["name"],
            "auth_backend": self.identifier,
        }

        return [user_data, id_token]

    def store_oidc_session(self, session_id, user, id_token):

        if not backchannel_logout_enabled:
            return

        if id_token is None:
            return

        sid = id_token["sid"]
        sub = id_token["sub"]
        iss = id_token["iss"]
        OIDCSession.objects.create(user=user,session_id=session_id,
                                   oidc_session_id=sid, oidc_user_id=sub, oidc_issuer=iss)

        logger.debug(f"Stored OIDC session for iss={iss} sub={sub} sid={sid} for session_id={session_id}")

    def delete_oidc_session(self, user, oidc_session_id, session_id):

        if session_id is None and user is None:
            # we always need at least a user to delete oidc sessions if no session_id is given
            return 0

        filter_args = {}

        if user is not None:
            filter_args["user_id"] = user.id

        if oidc_session_id is not None:
            # if a specific oidc_session_id should be deleted
            filter_args["oidc_session_id"] = oidc_session_id

        if session_id is not None:
            # if a specific session_id should be deleted
            filter_args["session_id"] = session_id

        oidc_sessions = list(OIDCSession.objects.filter(**filter_args))
        deleted_oidc_sessions = 0
        if len(oidc_sessions) > 0:
            for oidcSession in oidc_sessions:
                # delete all oidcSessions referenced by that user on logout
                oidcSession.delete()
                deleted_oidc_sessions += 1

        return deleted_oidc_sessions

    def process_backchannel_logout(self, request):
        """
        Process an OIDC back-channel logout request.

        Validates the logout token, identifies matching OIDC sessions by issuer,
        subject, and/or session ID, deletes associated Django sessions, and removes
        persisted OIDCSession records. Returns a JSON-serializable status dict.
        """
        if not backchannel_logout_enabled:
            return {
                "status": "logout_error",
                "error": "backchannel_logout_disabled",
                "error_description": "OIDC Back-channel logout is not enabled for this backend",
            }

        try:
            logout_token = self._parse_logout_token(request)
        except Exception as err:
            return {
                "status": "logout_error",
                "error": "invalid_request",
                "error_description": "Failed to validate in logout_token: {}".format(err)
            }

        jti = logout_token.get("jti", None)
        iss = logout_token.get("iss", None)
        sub = logout_token.get("sub", None)
        sid = logout_token.get("sid", None)
        if sub is None and sid is not None:
            return {
                "status": "logout_error",
                "error": "invalid_request",
                "error_description": "Missing sub or sid claim in logout_token"
            }

        logger.debug(f"Processing OIDC back-channel logout for jti={jti} iss={iss} sub={sub} sid={sid}")

        filter_args = {}
        if sub is not None:
            filter_args["oidc_user_id"] = sub
        if sid is not None:
            filter_args["oidc_session_id"] = sid
        if iss is not None:
            filter_args["oidc_issuer"] = iss

        oidc_sessions = list(OIDCSession.objects.filter(**filter_args))

        deleted_sessions_count = 0
        deleted_oidc_sessions_count = 0
        if len(oidc_sessions) > 0:
            for oidcSession in oidc_sessions:
                sessions = Session.objects.filter(session_key=oidcSession.session_id)
                if len(sessions) > 0:
                    for session in sessions:
                        session.delete()
                        deleted_sessions_count += 1
                    user_logged_out.send(sender=OIDCAuthBackend.__class__, request=request, user=oidcSession.user)
                oidcSession.delete()
                deleted_oidc_sessions_count += 1

        logger.debug(f"Deleted sessions for OIDC back-channel logout for jti={jti} iss={iss} sub={sub} sid={sid}. "
                     f"deleted_sessions={deleted_sessions_count} deleted_oidc_sessions={deleted_oidc_sessions_count}")

        return {"status": "logged_out"}

    def _parse_logout_token(self, request):
        """
        Parse and validate an OIDC back-channel logout token.

        Extracts the logout_token from the POST body and verifies it against the
        configured client (audience, issuer, key material). Returns the decoded
        logout_token claims on success or an error dict on failure.
        """

        req = BackChannelLogoutRequest().from_urlencoded(request.body.decode("utf-8"))
        verify_args = {"aud": self.client.client_id, "iss": self.client.issuer, "keyjar": self.client.keyjar}

        # parse / validate logout token
        try:
            req.verify(**verify_args)
        except Exception as err:
            return {
                "status": "logout_error",
                "error": "invalid_request",
                "error_description": "Failed to validate in logout_token: {}".format(err)
            }

        return req["logout_token"]

@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """
    Cleanup OIDC sessions on user logout.

    Removes all stored OIDCSession entries for the logged-out user, unless
    back-channel logout is disabled or the logout was triggered internally
    by the OIDC backend itself.
    """
    if not backchannel_logout_enabled:
        return

    # ignore our own back-channel logout signals
    if sender == OIDCAuthBackend.__class__:
        return

    oidc_sessions = list(OIDCSession.objects.filter(user_id=user.id))
    oidc_session_count = len(oidc_sessions)
    if oidc_session_count > 0:
        for oidcSession in oidc_sessions:
            # delete all oidc_sessions referenced by that user on logout
            oidcSession.delete()

        logger.debug(f"Removed OIDCSessions for user logout. user_id={user.id} oidc_sessions_removed={oidc_session_count}.")

    def __getstate__(self):
        logger.info("Serializing OIDCAuthBackend for caching")
        return {}
        return {
            "op_info": self.op_info,
            "client_reg": self.client_reg,
            "jwks": {
                issuer: self.client.keyjar.export_jwks(issuer=issuer, private=True)
                for issuer in self.client.keyjar.issuer_keys.keys()
            }
        }

auth_backend_lifetime = config.getint("oidc", "lifetime", fallback=3600)


def get_auth_backend():
    data = cache.get(CACHE_KEY, None)
    if data is None:
        auth_backend = OIDCAuthBackend()
        logger.info("Storing new auth backend in cache")
        cache.set(CACHE_KEY, auth_backend, auth_backend_lifetime)
    else:
        logger.info("Using cached auth backend")
        # ToDo implement restore from data
        auth_backend = OIDCAuthBackend()
    return auth_backend