from rest_framework import pagination

class CustomLimitOffsetPagination(pagination.LimitOffsetPagination):
    default_limit = 40
    max_limit = 100
