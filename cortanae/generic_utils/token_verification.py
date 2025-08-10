from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, timedelta
from apps.users.models import TokenValidator
from decouple import config
from typing import Tuple, Optional

User = get_user_model()

TOKEN_EXPIRY_MINUTES = config("TOKEN_EXPIRY_MINUTES")


def verify_token(
    token_instance: TokenValidator,
) -> Tuple[bool, Optional[User], str]:
    """
    Verifies a token and returns a tuple of:
    (is_valid, user_instance_or_none, reason)

    reason is useful for returning error messages directly in views/serializers.
    """
    if not token_instance:
        return False, None, "Token not found"

    if timezone.now() > (
        token_instance.created_at + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
    ):
        token_instance.delete()
        return False, None, "Token expired"

    try:
        user_instance = User.objects.get(email=token_instance.email)
    except User.DoesNotExist:
        return False, None, "User not found"

    token_generator = PasswordResetTokenGenerator()
    if not token_generator.check_token(user_instance, token_instance.token):
        return False, None, "Invalid token"

    token_instance.delete()
    return True, user_instance, "Token valid"
