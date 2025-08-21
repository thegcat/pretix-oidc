# pretix OIDC

This is a plugin for [pretix](https://github.com/pretix/pretix).

OIDC authentication plugin for pretix

## Installation

Activate the virtual environment for your pretix installation and run

    pip install pretix-oidc

To activate the OIDC authentication mechanism add
`pretix_oidc.auth.OIDCAuthBackend` to the list of `pretix.auth_backends` in
your `pretix.cfg`. Add the OIDC configuration to that same file in a new
`oidc` section, values without a default are mandatory:

    [oidc]
    # label on the login button,
    # default: Login with OpenID connect
    title=
    # OIDC URIs, can generally be found unter .well-known/openid-configuration
    # of your OIDC endpoint
    issuer=
    authorization_endpoint=
    token_endpoint=
    userinfo_endpoint=
    end_session_endpoint=
    jwks_uri=
    # OIDC client ID and secret
    client_id=
    client_secret=
    # comma-separated list of scopes to request
    # default: openid
    # recommended: openid,email,profile
    scopes=
    # what OIDC claim pretix should use to uniquely identify OIDC users
    # default: sub
    unique_attribute=
    # set staff scope to an scope name (maybe you need to add it to scopes as well) and a value to test against to promote users as staff
    staff_scope=
    staff_value=
    # multiple staff_values can be provided, separated by commas. whitespaces are ignored.
    # staff_value=val_1,val_2

The callback URI on your pretix will be `/oidc/callback/`, enter this at the
appropriate place in your OIDC provider.

Please note that all users with the permission to change organizer settings
will have access to the team assignment rules. Those rules can add users to a
specific team based on an arbitrary OIDC claim when the users log in, this
means that users with the permission to change organizer settings might be
able to enumerate users with a certain OIDC claim when the users log in and
can lead to a data leak.

## Configuration

Users belonging to a team with the permission to change organizer settings can
add team assignment rules on the organizer page > team assignment rules. Users
can be added to a specific team of that organizer based on the value of
arbitrary OIDC attributes (claims). Team assignment rules will apply when
users log in, users matching newly created rules might need to log out and
back in for the assignment to take effect.

## Development setup

1. Make sure that you have a working [pretix development
   setup](https://docs.pretix.eu/en/latest/development/setup.html).
2. Clone this repository.
3. Activate the virtual environment you use for pretix development.
4. Execute `python setup.py develop` within this directory to register
   this application with pretix\'s plugin registry.
5. Execute `make` within this directory to compile translations.
6. Restart your local pretix server. You can now use the plugin from
   this repository for your events by enabling it in the \'plugins\'
   tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check
locally, you need these packages installed:

    pip install flake8 isort black

To check your plugin for rule violations, run:

    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running:

    isort .
    black .

To automatically check for these issues before you commit, you can run
`.install-hooks`.

## License

Copyright 2023 Jaakko Rinta-Filppula, Felix Schäfer

Released under the terms of the Apache License 2.0
