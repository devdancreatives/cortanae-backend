from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.kyc.urls")),
    path("api/", include("apps.transactions.urls")),
    # Swagger URLs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/docs/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/", include("apps.accounts.urls")),
    path("api/chats/", include("apps.chat.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
]
