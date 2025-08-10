from typing import Any

from django.conf import settings
from django.core.mail import send_mail, send_mass_mail, get_connection
from django.template.loader import render_to_string


class Mailer:
    """
    class to handle sending of mails
    """

    def __init__(self):
        self.sender = settings.DEFAULT_FROM_EMAIL
        self.password = settings.EMAIL_HOST_PASSWORD

    def reset_connection(self, username, password):
        if not username:
            username = self.sender
        if not password:
            password = self.password
        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            use_ssl=True,
            username=username,
            password=password,
        )
        return connection

    def _create_message(self, template, content: dict[str, Any]) -> str:
        """_summary_

        Args:
                template (_type_): _description_
                content (dict[str, Any]): _description_

        Returns:
                str: _description_
        """
        if not content:
            raise ValueError("No content provided")
        if not template:
            raise ValueError("No template provided")
        if template:
            data = render_to_string(template, content)
            return data

    def mail_send(
        self,
        title: str,
        content: dict[str, Any],
        recipient: str,
        template: str,
        sender: str = "",
        message: str = "",
        password: str = "",
    ) -> None:
        try:
            content = self._create_message(template, content)
            if not sender:
                sender = self.sender
            if not password:
                password = self.password
            email_connection = self.reset_connection(sender, password)
            send_mail(
                title,
                message,
                from_email=sender,
                recipient_list=[recipient],
                html_message=content,
                fail_silently=False,
            )
        except Exception as e:
            # log the error somewhere
            return e

    def mail_send_bulk(
        self,
        title: str,
        content: dict[str, Any],
        recipients: list[str],
        template: str,
        sender: str = "",
        message: str = "",
    ) -> None:
        try:
            content = self._create_message(template, content)
            if sender is None:
                sender = self.sender
            send_mass_mail(
                title,
                message,
                sender,
                recipients,
                html_content=content,
            )
        except Exception as e:
            return e


mail_service = Mailer()
__all__ = ["mail_service"]
