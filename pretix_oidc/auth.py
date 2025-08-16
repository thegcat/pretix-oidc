import logging
import time
from django.urls import reverse
from oic import rndstr
from oic.oic import Client
from oic.oic.message import (
    AuthorizationResponse,
    ProviderConfigurationResponse,
    RegistrationResponse,
)
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from pretix.base.auth import BaseAuthBackend
from pretix.settings import config

logger = logging.getLogger(__name__)


class OIDCAuthBackend(BaseAuthBackend):
    def __init__(self):
        try:
            self.title = config.get(
                "oidc", "title", fallback="Login with OpenID connect"
            )

            op_info = ProviderConfigurationResponse(
                version="1.0",
                issuer=config.get("oidc", "issuer"),
                authorization_endpoint=config.get("oidc", "authorization_endpoint"),
                token_endpoint=config.get("oidc", "token_endpoint"),
                userinfo_endpoint=config.get("oidc", "userinfo_endpoint"),
                end_session_endpoint=config.get("oidc", "end_session_endpoint"),
                jwks_uri=config.get("oidc", "jwks_uri"),
            )

            client_reg = RegistrationResponse(
                client_id=config.get("oidc", "client_id"),
                client_secret=config.get("oidc", "client_secret"),
            )

            self.client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
            self.client.handle_provider_config(op_info, op_info["issuer"])
            self.client.store_registration_info(client_reg)
            self.client.redirect_uris = [None]

            self.scopes = config.get("oidc", "scopes", fallback="openid").split(",")
        except KeyError:
            logger.error(
                "Please specify issuer, authorization_endpoint, token_endpoint, userinfo_endpoint, end_session_endpoint, jwks_uri, client_id and client_secret "
                "in [oidc] section in pretix.cfg"
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
