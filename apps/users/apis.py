from rest_framework.permissions import IsAuthenticated


from django.forms import ValidationError
from django.core.validators import validate_email
from rest_framework.response import Response
from .models import TokenValidator, User
from .serializers import (
    PasswordChangeSerializer,
    UserRegisterSerializer,
)
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from .serializers import (
    VerifyAccountSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    PasswordChangeSerializer,
    UserLoginSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return response


class RegisterAPIView(CreateAPIView):
    """
    User Registration Endpoint

    Allows a user to register using email, password, first name, and last name.
    """

    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class EmailAvailaibilityView(APIView):
    """
    Confirm email availaibility before proceeding with Registration

    return - Response object
    """

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if email is None:
            return Response(
                {"detail": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"detail": "Invalid email format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email.lower()).exists()

        if user:
            return Response(
                {"detail": "Email address already in use"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"detail": "Email address is available."},
            status=status.HTTP_200_OK,
        )


class VerifyAccount(CreateAPIView):
    serializer_class = VerifyAccountSerializer
    queryset = TokenValidator.objects.all()

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        serializer.save()


class PasswordResetRequestView(CreateAPIView):
    serializer_class = PasswordResetRequestSerializer
    queryset = TokenValidator.objects.all()

    def post(self, request):
        email = request.data.get("email", None)
        if not email:
            return Response(
                "Email not provided", status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=email)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Password reset mail sent", status=status.HTTP_200_OK)


class PasswordResetView(CreateAPIView):
    serializer_class = PasswordResetSerializer
    queryset = User.objects.all()

    def post(self, request) -> Response:
        token = request.data.get("token", None)
        if not token:
            return Response(
                "No token provided", status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            "Password successfully reset", status=status.HTTP_200_OK
        )


class PasswordChangeView(UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )
