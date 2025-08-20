from django.urls import path
from .apis import (
    CustomTokenObtainPairView,
    EmailAvailaibilityView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetView,
    RegisterAPIView,
    VerifyAccount,
    UserDetailsAPIView
)

urlpatterns = [
    path("register/", RegisterAPIView.as_view()),
    path("mail-check/", EmailAvailaibilityView.as_view()),
    path("login/", CustomTokenObtainPairView.as_view()),
    path("password-reset/request/", PasswordResetRequestView.as_view()),
    path("password-reset/", PasswordResetView.as_view()),
    path("update-password/", PasswordChangeView.as_view()),
    path("verify-account/", VerifyAccount.as_view()),
    path("user/me/", UserDetailsAPIView.as_view(), name="user_details_api"),
 
]
