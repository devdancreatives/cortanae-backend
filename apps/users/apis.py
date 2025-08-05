from rest_framework import generics, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from .models import User
from .serializers import UserRegisterSerializer


class RegisterAPIView(generics.CreateAPIView):
    """
    User Registration Endpoint

    Allows a user to register using email, password, first name, and last name.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

