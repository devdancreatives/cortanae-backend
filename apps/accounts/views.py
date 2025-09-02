from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response, status

from apps.accounts.serializers import (
    AccountCreateSerializer,
    AccountPinChangeSerializer,
)
from .models import Account
from apps.users.models import User
from apps.users.serializers import UserSerializer

# Create your views here.


class UpdateAccountPinVIew(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Account.objects.all()
    serializer_class = AccountPinChangeSerializer

    def get_object(self):
        account = Account.objects.filter(user=self.request.user).first()
        if not account:
            return None
        return account

    def patch(self, request, *args, **kwargs):
        account = self.get_object()
        if not account:
            return Response(
                {"detail": "User does not have an account"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            account, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
