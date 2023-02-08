import json
from datetime import datetime, timedelta
import pytz

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.timezone import activate
from django.core.validators import RegexValidator

import google.auth.transport.requests
import google.oauth2.credentials
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from django import forms


User = get_user_model()

# Google related views
# See https://developers.google.com/identity/protocols/oauth2/web-server#python
scopes = {
    "base": ["openid",
             "https://www.googleapis.com/auth/userinfo.email"],
    "cal_scopes": ["https://www.googleapis.com/auth/calendar.events",
                   "https://www.googleapis.com/auth/calendar.calendarlist"],
    "base_email_scopes": [
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.metadata",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.metadata"],
    "read_email_scopes": [
        "https://www.googleapis.com/auth/gmail.readonly"]
    }
API_SERVICE_NAME = "calendar"
API_VERSION = "v3"


# We use a regular form instead of model form because we want the account id (e.g. two users _could_ add the same google account
# so this way we know were modifying the correct users google account).
class UpdateGoogleAccountForm(forms.Form):
    account_id = forms.CharField(label='Account ID', max_length=200, required=True, widget=forms.HiddenInput)
    calendar_sync_enabled = forms.BooleanField(label="Calendar Sync", required=False)
    second_chance_email = forms.BooleanField(label="2nd chance e-mail", required=False)
    delete_events_from_email = forms.BooleanField(label="Delete events based on email", required=False)


class GoogleAccount(models.Model):
    account_id = models.AutoField(primary_key=True, null=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    google_user_email = models.CharField(max_length=250, null=False)
    credentials = models.CharField(max_length=5000, null=False)
    credential_expiry = models.DateTimeField(null=True)
    last_refreshed = models.DateTimeField(default=datetime.now)
    unique_together = ["user", "google_user_email"]
    calendar_sync_enabled = models.BooleanField(default=True)
    second_chance_email = models.BooleanField(default=False)
    more_spam_filter = models.BooleanField(default=False)
    delete_events_from_email = models.BooleanField(default=False)

    @property
    def scopes(self):
        creds = self.get_credentials()
        return creds.scopes

    def get_friendly_scopes(self):
        friendly_scopes = []
        try:
            account_scopes = self.scopes
            for scope_name in scopes.keys():
                scope_values = scopes[scope_name]
                if all(map(lambda scope: scope in account_scopes, scope_values)):
                    friendly_scopes.append(scope_name)
        except:
            return ["Account re-add required."]
        return friendly_scopes

    def get_credentials(self):
        stored_creds = json.loads(self.credentials)
        # Get expirery so we can figure out if we need a refresh
        if self.credential_expiry is not None:
            stored_creds["expiry"] = self.credential_expiry
        else:
            stored_creds["expiry"] = datetime.now()

        # Drop timezone info
        stored_creds["expiry"] = stored_creds["expiry"].replace(tzinfo=None)
        user_credentials = google.oauth2.credentials.Credentials(**stored_creds)
        if user_credentials.expired:
            http_request = google.auth.transport.requests.Request()
            user_credentials.refresh(http_request)
        self.credentials = user_credentials.to_json()
        self.credential_expiry = user_credentials.expiry
        self.save()
        return user_credentials

    def calendar_service(self):
        return build(API_SERVICE_NAME, API_VERSION, credentials=self.get_credentials())

    def refresh_calendars(self):
        """Refresh the user calendars. Defined here so we can share refresh logic."""
        current_cals = self.calendar_service().calendarList().list().execute()
        for cal in current_cals['items']:
            deleted = "deleted" in cal and cal["deleted"]
            UserCalendar.objects.update_or_create(
                user=self.user,
                google_account=self,
                google_calendar_id=cal['id'],
                defaults={"deleted": deleted, "name": cal['summary']})

    def get_config_form(self):
        f = UpdateGoogleAccountForm()
        f.fields["account_id"].initial = self.account_id
        f.fields["calendar_sync_enabled"].initial = self.calendar_sync_enabled
        f.fields["second_chance_email"].initial = self.second_chance_email
        f.fields["delete_events_from_email"].initial = self.delete_events_from_email
        return f


    class Meta:
        app_label = "cal_sync_magic"


class UserCalendar(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    internal_calendar_id = models.AutoField(primary_key=True)
    google_account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE, null=False)
    google_calendar_id = models.CharField(max_length=500, null=False)
    name = models.CharField(max_length=500, null=True, blank=True)
    last_error = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)
    last_sync_token = models.CharField(max_length=500, null=True, blank=True)
    webhook_enabled = models.BooleanField(default=False) # See https://developers.google.com/calendar/api/guides/push

    def __str__(self):
        return self.name

    def handle_event(self, event):
        syncs = SyncConfigs.objects.filter(
            user = self.user,
            eventgroups__contains = self)
        rules = CalendarRules.objects.filter(
            user = self.user,
            calendars__contains = self)

        for s in sync:
            s.handle_event(e)
        for r in rules:
            r.handle_event(e)

    def get_event(self, id):
        calendar_service = self.google_account.calendar_service()
        return calendar_service.events().get(
            calendarId=self.google_calendar_id,
            eventId=id)
    
    def add_event(self, event):
        calendar_service = self.google_account.calendar_service()
        calendar_service.events().insert(
            calendarId=self.google_calendar_id,
            body=event,
            sendUpdates="none").execute()

    def patch_event(self, event):
        calendar_service = self.google_account.calendar_service()
        calendar_service.events().patch(
            calendarId=self.google_calendar_id,
            eventId=event["id"],
            body=event,
            sendUpdates="none").execute()

    def get_changes(self):
        """Get the event changes since the last sync. This _may_ return all calendar events.
        See https://developers.google.com/calendar/api/guides/sync"""
        calendar_service = self.google_account.calendar_service()
        # Make initial events request
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        timeMax = (datetime.utcnow() + relativedelta(years=50)).isoformat() + 'Z'
        cal_req = calendar_service.events().list(
            calendarId= self.google_calendar_id,
            timeMin=now,
            timeMax=timeMax,
            maxResults=5000,
            # Expands re-occuring events out, required for startTime ordering.
            singleEvents=True,
            syncToken=self.last_sync_token,
            orderBy='startTime')
        try:
            events = cal_req.execute()
        except Exception:
            cal_req = calendar_service.events().list(
                calendarId=self.google_calendar_id,
                timeMin=now,
                timeMax=timeMax,
                maxResults=5000,
                singleEvents=True, # Expands re-occuring events out, required for startTime ordering.
                orderBy='startTime')
        collected_events = events["items"]
        while "nextPageToken" in events:
            cal_req = calendar_service.events().list(previous_request=cal_req, previous_response=exents)
            events = cal_req.execute()
            collected_events += events["items"]
            self.last_sync_token = events["syncToken"]
            self.save()
        return collected_events


    class Meta:
        app_label = "cal_sync_magic"

class SyncConfigs(models.Model):
    """
    Configuration of a sink between two calendars.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    src_calendars = models.ManyToManyField(
        'UserCalendar', related_name='src_calendars')
    sink_calendars = models.ManyToManyField(
        'UserCalendar', related_name='sink_calendars')
    hide_details = models.BooleanField(default=False)
    default_title = models.CharField(max_length=100, null=True, blank=True)
    match_title_regex = models.CharField(max_length=1000, null=True, blank=True)
    match_creator_regex = models.CharField(max_length=1000, null=True, blank=True)
    rewrite_regex = models.CharField(max_length=1000, null=True, blank=True)
    invitee_skip_event_threshold = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.src_calendars.all()} to {self.sink_calendars.all()}"

    def handle_event(self, event):
        # No self propegating loops.
        if ("source" in cleaned_event
            and cleaned_event["source"] == "https://www.pigscanfly.ca/calendars/"):
            return
        for s in sink_calendars.filter(user=self.user):
            cleaned_event = event
            if self.default_title is not None:
                if (self.match_title_regex is not None and
                    re.search(self.match_title_regex, cleaned_event["title"]) is None):

                    cleaned_event["title"] = default_title
            if self.hide_details:
                cleaned_event["description"] = "Magical synced calendar event."
            cleaned_event["privateCopy"] = True
            cleaned_event["source"] = "https://www.pigscanfly.ca/calendars/"
            cleaned_event["attendees"] = []
            current_event = s.get_event(id=event["id"])
            if current_event is None:
                s.add_event(cleaned_event)
            else:
                if cleaned_event["source"] == "https://www.pigscanfly.ca/calendars/":
                    s.patch_event(cleaned_event)
                else:
                    print("Skipping sync back, looks like OG event.")
    class Meta:
        app_label = "cal_sync_magic"


class CalendarRules(models.Model):
    """
    Configuration for rules to attempt to apply to calendar events as they come in.
    """
    min_sched = models.DurationField(null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    calendars = models.ManyToManyField(
        'UserCalendar', related_name='rule_calendars')
    warn_location_mismatch = models.BooleanField(default=False)
    allow_list_min_sched = models.CharField(max_length=1000, null=True, blank=True)
    # We call this the "west coast field."
    soft_maybe_conflict = models.BooleanField(default=False)
    # We call this the "east coast field."
    decline_conflict = models.BooleanField(default=False)
    allow_list_conflict = models.CharField(max_length=1000, null=True, blank=True)
    # Delete canceled flights and stuff
    try_to_delete_canceled_events = models.BooleanField(default=False)

    def __str__(self):
        r = ""
        for field in self._meta.fields:
            try:
                name = field.name
                value = field.value_to_string(self)
                if value is None:
                    r = f"{r}\n{name} -> None"
                else:
                    r = f"{r}\n{name} -> {value}"
            except Exception as e:
                r = f"{r}{e}"
        return r

    class Meta:
        app_label = "cal_sync_magic"

    def get_min_sched_allow(self):
        if self.allow_list_min_sched is None:
            return []
        else:
            return self.allow_list_min_sched.split(",")

    def evaluate_rule(self, event):
        """Evaluate a rule and take the configured action on it."""
        self.evaluate_schedule(event)

    def evaluate_schedule(self, event):
        if self.min_sched is not None:
            now = datetime.utcnow()
            event_start = iso8601.parse_date(event.start.dateTime)
            if ((now - event_start) < self.min_sched and
                creator.email not in self.get_min_sched_allow() and
                event["source"] is None and event["creator"] is not None and
                event["creator"]["email"] is not None):

                from django.core.mail import send_mail
                subject_line = f"Invite to {event.summary}"
                if event["creator"]["DisplayName"] is not None:
                    subject_line = f"Invite to {event.summary} from {event.creator.DisplayName}"
                send_email(
                    subject_line,
                    event["creator"]["email"],
                    "calendar-magic@pigscanfly.ca",
                    f"FYI the invite to this event was sent with less than {self.min_sched} " +
                    f" notice so {self.google_user_email} may not make it."
                )



class NewSync(forms.ModelForm):
    class Meta:
        model = SyncConfigs
        fields = ['src_calendars', 'sink_calendars', 'hide_details',
                  'default_title', 'invitee_skip_event_threshold', 'user']

    def __init__(self, *args, user=None, calendars=None, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        if calendars is not None:
            self.fields["src_calendars"].queryset = calendars
            self.fields["sink_calendars"].queryset = calendars
        if user is not None:
            user_field = self.fields["user"]
            user_field.initial = user
            user_field.widget = user_field.hidden_widget()
            user_field.validator = RegexValidator(regex=f"^{user}$")


class NewCalRule(forms.ModelForm):
    class Meta:
        model = CalendarRules
        # Exclude the not yet implemented features
        exclude = ["warn_location_mismatch", "soft_maybe_conflict", "decline_conflict",
                   "allow_list_conflict", "try_to_delete_canceled_events"]

    def __init__(self, *args, calendars=None, user=None, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        if calendars is not None:
            self.fields["calendars"]._choices = (
                calendars
            )
        if user is not None:
            user_field = self.fields["user"]
            user_field.initial = user
            user_field.widget = user_field.hidden_widget()
            user_field.validator = RegexValidator(regex=f"^{user}$")
