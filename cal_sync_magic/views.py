from django.urls import redirect, reverse
from django.utils.decorators import method_decorator
from django.views import View

from googleapiclient.discovery import build

# Google related views
# See https://developers.google.com/identity/protocols/oauth2/web-server#python
scopes = ["https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/userinfo.email"]
API_SERVICE_NAME = "calendar"
API_VERSION = "v3"

class GoogleAuthView(View):
    def get(request):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE, scopes=SCOPES)
        flow.redirect_uri = reverse("google-oauth-callback")
        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')
        request.session['google_auth_state'] = state
        # Redirect the user to the authorization url
        return redirect(authorization_url)

class GoogleCallBackView(View):
    def get(request):
        state = request.session['google_auth_state']
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
        flow.redirect_uri = reverse("google-oauth-callback")
        authorization_response = request.GET.get("url")
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        google_user_email = user_info['email']
        account = GoogleAccount.update_or_create(
            user = request.user,
            google_user_email=google_user_email,
            defaults={
                "credentials": credentials,
                "last_refreshed": datetime.now()})
        return redirct(reverse("config-sync"))

class ConfigureSyncs(View):
    def get(request):
        return "farts"
        

