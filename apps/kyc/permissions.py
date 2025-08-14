from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerKYC(BasePermission):
    """
    Allows access only to the owner of the KYC object.
    For /kyc/me/ we handle object via get_object (request.user.kyc_profile).
    """
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
