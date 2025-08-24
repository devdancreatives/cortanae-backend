from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from apps.transactions.serializers import (
    DepositSerializer,
    TransactionHistorySerializer,
    TransactionSerializer,
    TransferSerializer,
)
from .models import Transaction, TransactionHistory
from rest_framework import status
from rest_framework.response import Response

# Create your views here.


class DepositView(CreateAPIView):
    serializer_class = DepositSerializer
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {"message": "Deposit successful", "data": response.data},
            status=status.HTTP_201_CREATED,
        )


class TransferView(CreateAPIView):
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()


class UserTransactionsHistoryView(ListAPIView):
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_account = getattr(user, "user_accounts", None)

        base_q = Q(transaction__initiated_by=user)  # ✅ correct relation prefix

        # Add account-based filters only if account exists
        if user_account:
            base_q |= Q(transaction__source_account=user_account) | Q(
                transaction__destination_account=user_account
            )

        qs = (
            TransactionHistory.objects
            .select_related("transaction")  # perf
            .filter(base_q)
            .order_by("-created_at")
        )

        # Debug logs
        print(
            "[DEBUG] UserTransactionsHistoryView",
            f"user_id={getattr(user, 'id', None)}",
            f"user_account_id={getattr(user_account, 'id', None)}",
            f"count={qs.count()}",
        )
        return qs


class TransactionInformationView(RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "reference"

    def get_queryset(self):
        # check to confirm that the user views only his/her transaction
        user = self.request.user
        try:
            user_account = user.user_accounts
        except AttributeError:
            return Transaction.objects.none()

        return Transaction.objects.filter(
            Q(initiated_by=user)
            | Q(source_account=user_account)
            | Q(destination_account=user_account)
        )

    def get_object(self):
        reference = self.kwargs.get("reference")
        queryset = self.get_queryset()

        transaction = get_object_or_404(queryset, reference=reference)
        return transaction
