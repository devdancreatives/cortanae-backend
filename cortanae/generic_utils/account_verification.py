from django.contrib.auth.tokens import PasswordResetTokenGenerator
from apps.users.models import TokenValidator

from django.contrib.auth import get_user_model
from decouple import config
from cortanae.generic_utils.mail_send import mail_service
from django.utils import timezone

User = get_user_model()

FE_URL = config("FRONT_END_URL")


def verification_mail(instance, mail_type):
    mail_type = mail_type.lower()

    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(instance)

    if mail_type == "verify_account":
        token_type = "verify_account"
        verification_url = f"{FE_URL}/auth/verify-account?q={token}"
        template = "account_verification.html"
        title = "Verify Your Cortanae Capital Bank Account"
        message = (
            "Please verify your account by clicking the link in this email."
        )
    elif mail_type == "reset_password":
        token_type = "reset_password"
        verification_url = f"{FE_URL}/auth/reset-password?q={token}"
        template = "password_reset.html"
        title = "Reset Your Cortanae Capital Bank Account Password"
        message = "Please click the link in this email to reset your password."
    else:
        raise ValueError(f"Unknown mail type: {mail_type}")

    TokenValidator.objects.create(user=instance,
        email=instance.email, token=token, token_type=token_type
    )

    content = {
        "user": instance,
        "verification_url": verification_url,
        "current_year": timezone.now().year,
    }

    mail_service.mail_send(
        title=title,
        content=content,
        recipient=instance.email,
        template=template,
        message=message,
    )
