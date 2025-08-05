import requests
from django.utils import timezone
from django.conf import settings
from rest_framework.permissions import BasePermission
from apps.core.models import APIKey
from apps.data_connector.models import VomeAppOrganizationSubscription


class HasAPIKey(BasePermission):
    def has_permission(self, request, view):
        # Retrieve API key from request headers
        api_key = request.headers.get('API-KEY')
        if not api_key:
            return False

        try:
            # Fetch the API key with the related institution in a single query
            api_key_instance = APIKey.objects.select_related(
                'institution').get(token=api_key)

            # Check if the API key is active
            if not api_key_instance.active:
                return False

            # Update the last_used field to the current time
            api_key_instance.last_used = timezone.now()
            api_key_instance.save()

            # Fetch the subscription for the institution from the 'vome' database
            vome_subscription = VomeAppOrganizationSubscription.objects.using('vome').filter(
                institution=api_key_instance.institution.vome_institution_id
            ).first()

            # If subscription exists and plan_type is not 4, deny access
            if vome_subscription and vome_subscription.plan_type != 4:
                return False

            # Attach institution to the request for further use
            request.institution = api_key_instance.institution.vome_institution_id

            return True
        except APIKey.DoesNotExist:
            return False


# Assign the permission class to be used globally or in specific views
generic_authenticated_user_permission = [HasAPIKey]


def validate_user_token(user_token):
    # Prepare the headers and the request payload
    headers = {
        'Content-Type': 'application/json',
        'token': f"{settings.INTEGRATION_APP_TOKEN}"

    }
    payload = {
        'user_token': user_token
    }
    api_url = f"{settings.VOME_APP_API}/api/integrations/token/validate/"
    try:
        # Send the POST request to the API
        response = requests.post(api_url, json=payload, headers=headers)

        # Check for successful response
        if response.status_code == 200:
            # print("content", response.json())
            return response.json()
        else:
            return {'error': f"Failed with status code {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        # Handle any exceptions during the request
        return {'error': f"An error occurred: {str(e)}"}


class HasValidUserToken(BasePermission):
    def has_permission(self, request, view):
        # Retrieve user token from request headers
        authorization_header = request.headers.get('Authorization')

        # The header format is expected to be "Bearer <token>"
        if not authorization_header.startswith('Bearer '):
            return False

        # Extract the token from the header
        user_token = authorization_header.split(' ')[1]

        # Call the function to validate the user token
        response = validate_user_token(user_token)

        # Check if the response contains 'institution_id'
        institution_id = response.get('institution_id')

        if institution_id:
            # Attach institution_id to request for further use
            request.institution_id = institution_id
            request.user_id = response.get('user_id')
            return True

        # If token is invalid or 'institution_id' not found, deny access
        return False


vome_app_generic_authenticated_user_permission = [HasValidUserToken]
