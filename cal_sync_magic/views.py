from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
User=get_user_model()

import google_auth_oauthlib
from googleapiclient.discovery import build

from cal_sync_magic.models import *


def get_redirect_uri(request):
    return str(request.build_absolute_uri(reverse("google-oauth-callback")))


class GoogleAuthView(LoginRequiredMixin, View):
    def get(self, request):
        required_scopes = request.GET.get("scopes", "cal_scopes")
        request_scopes = scopes["base"]
        for s in required_scopes.split(","):
            request_scopes += scopes[s]
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE, scopes=request_scopes)
        redirect_uri = get_redirect_uri(request)
        print(f"Redirect uri is {redirect_uri}")
        flow.redirect_uri = redirect_uri
        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')
        request.session['google_auth_state'] = state
        request.session['raw_scopes'] = request_scopes
        # Redirect the user to the authorization url
        return redirect(authorization_url)

class GoogleCallBackView(LoginRequiredMixin, View):
    def get(self, request):
        request_scopes = request.session['raw_scopes']
        state = request.session['google_auth_state']
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE, scopes=request_scopes, state=state)
        redirect_uri = get_redirect_uri(request)
        flow.redirect_uri = redirect_uri
        authorization_response = (redirect_uri + "?"
                                  + request.META['QUERY_STRING'])
        print(f"Auth response is {authorization_response}")
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        google_user_email = user_info['email']
        account = GoogleAccount.objects.update_or_create(
            user = request.user,
            google_user_email=google_user_email,
            defaults={
                "credential_expiry": credentials.expiry,
                "credentials": credentials.to_json(),
                "last_refreshed": datetime.now(),
            })
        return redirect(reverse("update-user-calendars"))

class UpdateUserCalendars(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        for account in GoogleAccount.objects.filter(user = request.user):
            account.refresh_calendars()
        return redirect(reverse("sync-config"))


class UpdateGoogleAccounts(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        form = UpdateGoogleAccountForm(request.POST)
        if form.is_valid():
            # Filter on user so folks can't update other peoples accounts settings
            google_account = GoogleAccount.objects.filter(
                user = request.user,
                account_id = form.cleaned_data['account_id']).get()
            google_account.calendar_sync_enabled = form.cleaned_data['calendar_sync_enabled']
            google_account.second_chance_email = form.cleaned_data['second_chance_email']
            google_account.delete_events_from_email = form.cleaned_data['delete_events_from_email']
            google_account.save()
            return redirect(reverse("sync-config"))
        else:
            raise Exception(f"Form validation failed - {form} from {request.POST}")

class ConfigureSyncs(LoginRequiredMixin, View):
    def get(self, request):
        google_accounts = GoogleAccount.objects.filter(user = request.user)
        calendars = UserCalendar.objects.filter(user = request.user)
        syncs = SyncConfigs.objects.filter(user = request.user)
        rules = CalendarRules.objects.filter(user = request.user)
        return render(request, 'configure_sync.html', context={
            'title': "Configure calendar syncing",
            'google_accounts': google_accounts,
            'calendars': calendars,
            'syncs': syncs,
            'rules': rules,
            'add_sync_form': NewSync(user=request.user, calendars=calendars),
            'add_cal_rule_form': NewCalRule(calendars=calendars, user=request.user)
            })


class DelRule(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        rule_id = request.POST.get("id")
        CalendarRules.objects.filter(user = user, id = rule_id).delete()
        return redirect(reverse("sync-config"))

class DelSync(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        sync_id = request.POST.get("id")
        SyncConfigs.objects.filter(user = user, id = sync_id).delete()
        return redirect(reverse("sync-config"))

class AddCalendarRule(LoginRequiredMixin, View):
    def post(self, request):
        user_form = NewCalRule(request.POST)
        if not user_form.is_valid():
            raise exception("Invalid form")
        if user_form.cleaned_data["user"] != self.request.user:
            raise Exception(f"user mismatch")
        user_form.save()
        return redirect(reverse("sync-config"))


class AddSync(LoginRequiredMixin, View):
    def post(self, request):
        calendars = UserCalendar.objects.filter(user = request.user)
        user_form = NewSync(request.POST, user=request.user, calendars=calendars)
        if not user_form.is_valid():
            raise exception("Invalid form")
        if user_form.cleaned_data["user"] != self.request.user:
            raise Exception(f"user mismatch")
        user_form.save()
        return redirect(reverse("sync-config"))

class ShowRawEvents(LoginRequiredMixin, View):
    def get(self, request, internal_id):
        google_accounts = GoogleAccount.objects.filter(user = request.user)
        calendar = UserCalendar.objects.filter(
            user = request.user,
            internal_calendar_id = internal_id).get()
        events = map(lambda x: json.dumps(x), calendar.get_changes())
        return render(request, 'debug_raw.html', context={
            "events": events})
