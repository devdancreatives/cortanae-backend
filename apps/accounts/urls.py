from django.urls import path

from apps.accounts.views import UpdateAccountPinVIew


urlpatterns = [path("account/pin-change", UpdateAccountPinVIew.as_view())]
