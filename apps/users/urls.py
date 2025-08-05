from django.urls import path
from .apis import RegisterAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
]