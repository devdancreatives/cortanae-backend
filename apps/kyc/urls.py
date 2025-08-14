from django.urls import path
from .views import KYCCreateAPIView, MyKYCView, KYCAdminStatusUpdateAPIView

app_name = "kyc"

urlpatterns = [
    path("kyc/", KYCCreateAPIView.as_view(), name="kyc-create"),
    path("kyc/me/", MyKYCView.as_view(), name="kyc-me"),
    path("kyc/<uuid:id>/status/", KYCAdminStatusUpdateAPIView.as_view(), name="kyc-status-update"),
]