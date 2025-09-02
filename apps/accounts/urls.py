from django.urls import path

from apps.accounts.views import UpdateAccountPinVIew, UserListAPIView


urlpatterns = [
    path("account/pin-change", UpdateAccountPinVIew.as_view()),
    path("users/", UserListAPIView.as_view(), name="user-list"),]
