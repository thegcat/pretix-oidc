import os
from distutils.command.build import build

from django.core import management
from setuptools import find_packages, setup

from pretix_oidc import __version__


try:
    with open(
        os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8"
    ) as f:
        long_description = f.read()
except Exception:
    long_description = ""


class CustomBuild(build):
    def run(self):
        management.call_command("compilemessages", verbosity=1)
        build.run(self)


cmdclass = {"build": CustomBuild}


setup(
    name="pretix-oidc",
    version=__version__,
    description="OIDC authentication plugin for pretix",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.fachschaften.org/kif/pretix-oidc",
    author="Jaakko Rinta-Filppula, Felix Schäfer",
    author_email="admin@kif.rocks",
    license="Apache",
    install_requires=["dictlib>=1.1.5", "oic>=1.2.0"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    cmdclass=cmdclass,
    entry_points="""
[pretix.plugin]
pretix_oidc=pretix_oidc:PretixPluginMeta
""",
)
