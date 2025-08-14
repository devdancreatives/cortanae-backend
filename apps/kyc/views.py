from rest_framework import status, generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import KYC
from .serializers import KYCSerializer, KYCWriteSerializer, KYCStatusUpdateSerializer
from .permissions import IsOwnerKYC


class KYCCreateAPIView(generics.CreateAPIView):
    """
    POST /api/kyc/
    Create KYC for authenticated user (only once).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KYCWriteSerializer

    def create(self, request, *args, **kwargs):
        print(f"[KYCCreateAPIView] user_id={request.user.id} creating KYC…")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read = KYCSerializer(instance)
        return Response(read.data, status=status.HTTP_201_CREATED)


class MyKYCView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/kyc/me/
    Retrieve or update the current user's KYC.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerKYC]
    serializer_class = KYCWriteSerializer  # used for PATCH

    def get_object(self):
        print(f"[MyKYCView.get_object] Fetching KYC for user_id={self.request.user.id}")
        return get_object_or_404(KYC, user=self.request.user)

    def get(self, request, *args, **kwargs):
        kyc = self.get_object()
        data = KYCSerializer(kyc).data
        return Response(data)

    def patch(self, request, *args, **kwargs):
        print(f"[MyKYCView.patch] user_id={request.user.id} updating KYC…")
        kyc = self.get_object()
        self.check_object_permissions(request, kyc)
        serializer = self.get_serializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(KYCSerializer(instance).data, status=status.HTTP_200_OK)


class KYCAdminStatusUpdateAPIView(generics.UpdateAPIView):
    """
    PATCH /api/kyc/{kyc_id}/status/
    Admin updates status (pending/approved/rejected) with optional error_message.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = KYCStatusUpdateSerializer
    queryset = KYC.objects.all()
    lookup_field = "id"

    def patch(self, request, *args, **kwargs):
        kyc = self.get_object()
        print(f"[KYCAdminStatusUpdateAPIView.patch] Admin updating KYC id={kyc.id}")
        serializer = self.get_serializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        print(f"[KYCAdminStatusUpdateAPIView.patch] KYC id={instance.id} new_status={instance.status}")
        return Response(KYCSerializer(instance).data, status=status.HTTP_200_OK)