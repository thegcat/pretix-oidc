from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^oidc/callback/', views.oidc_callback, name='oidc_callback'),
]
