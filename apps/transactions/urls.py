from django.urls import path

from apps.transactions.views import (
    DepositView,
    TransactionInformationView,
    TransferView,
    UserTransactionsHistoryView,
)


urlpatterns = [
    path(
        "transaction/deposit",
        DepositView.as_view(),
        name="Deposit into account",
    ),
    path(
        "transaction/:reference/view",
        TransactionInformationView.as_view(),
        name="Transaction information",
    ),
    path(
        "transaction/user-history",
        UserTransactionsHistoryView.as_view(),
        "user transaction history",
    ),
    path("transaction/transfer", TransferView.as_view()),
]
