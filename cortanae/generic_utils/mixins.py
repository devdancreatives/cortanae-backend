from rest_framework.exceptions import AuthenticationFailed
from core.models import APIKey


class APIKeyMixin:
    def authenticate_api_key(self, request):
        api_key = request.headers.get('API-Key')
        if not api_key:
            raise AuthenticationFailed('API key is required')

        try:
            api_key_instance = APIKey.objects.get(key=api_key)
            # Attach the institution to the request for later use
            request.institution = api_key_instance.institution
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')
