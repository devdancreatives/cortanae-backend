from django.urls import path

from apps.transactions.apis import (
    DepositView,
    TransactionInformationView,
    TransferView,
    UserTransactionsHistoryView,
)

urlpatterns = [
    path(
        "transaction/deposit/",
        DepositView.as_view(),
        name="deposit_into_account",
    ),
    path(
        "transaction/<uuid:reference>/view/",
        TransactionInformationView.as_view(),
        name="transaction_information",
    ),
    path(
        "transaction/user-history/",
        UserTransactionsHistoryView.as_view(),
        name="user_transaction_history",
    ),
    path("transaction/transfer/", TransferView.as_view()),
]
