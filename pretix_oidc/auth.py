import logging

from django.urls import reverse

from oic import rndstr
from oic.oic import Client
from oic.oic.message import AuthorizationResponse, ProviderConfigurationResponse, RegistrationResponse
from oic.utils.authn.client import CLIENT_AUTHN_METHOD

from pretix.base.auth import BaseAuthBackend
from pretix.settings import config

logger = logging.getLogger(__name__)


class OIDCAuthBackend(BaseAuthBackend):
    def __init__(self):
        try:
            self.config = config['oidc']

            self.title = self.config.get('title', 'Login with OpenID connect')

            op_info = ProviderConfigurationResponse(
                version='1.0',
                issuer=self.config['issuer'],
                authorization_endpoint=self.config['authorization_endpoint'],
                token_endpoint=self.config['token_endpoint'],
                userinfo_endpoint=self.config['userinfo_endpoint'],
                end_session_endpoint=self.config['end_session_endpoint'],
                jwks_uri=self.config['jwks_uri']
            )

            client_reg = RegistrationResponse(
                client_id=self.config['client_id'],
                client_secret=self.config['client_secret'],
            )

            self.client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
            self.client.handle_provider_config(op_info, op_info['issuer'])
            self.client.store_registration_info(client_reg)
            self.client.redirect_uris = [None]

            self.scopes = self.config.get('scopes', 'openid').split(',')
        except KeyError:
            logger.error("Please specify issuer, authorization_endpoint, token_endpoint, userinfo_endpoint, end_session_endpoint, jwks_uri, client_id and client_secret in [oidc] section in pretix.cfg")

    @property
    def identifier(self):
        return 'pretix_oidc'

    @property
    def verbose_name(self):
        return self.title

    def authentication_url(self, request):
        request.session['oidc_state'] = rndstr()
        request.session['oidc_nonce'] = rndstr()

        auth_req = self.client.construct_AuthorizationRequest(
            request_args={
                'client_id': self.client.client_id,
                'response_type': 'code',
                'scope': self.scopes,
                'nonce': request.session['oidc_nonce'],
                'redirect_uri': self.redirect_uri(request),
                'state': request.session['oidc_state']
            }
        )

        return auth_req.request(self.client.authorization_endpoint)

    def redirect_uri(self, request):
        return request.build_absolute_uri(reverse('plugins:pretix_oidc:oidc_callback'))

    def process_callback(self, request):
        auth_response = self.client.parse_response(
            AuthorizationResponse,
            info=request.META['QUERY_STRING'],
            sformat='urlencoded'
        )

        # if auth_response is not AuthorizationResponse:
        #     raise Exception('Invalid authorization response')

        if auth_response['state'] != request.session['oidc_state']:
            return [None, None]

        access_token_response = self.client.do_access_token_request(
            state=auth_response['state'],
            scope=self.scopes,
            request_args={
                'code': auth_response['code'],
                'redirect_uri': self.redirect_uri(request),
            },
            authn_method='client_secret_basic'
        )

        id_token = access_token_response['id_token']
        user_data = {
            'email': id_token['email'],
            'fullname': id_token['name'],
            'auth_backend': self.identifier,
        }

        return [user_data, id_token]
