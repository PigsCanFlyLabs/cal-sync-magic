import json
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import activate

import google.auth.transport.requests
import google.oauth2.credentials
import pytz
import requests
from dateutil.relativedelta import relativedelta
from google.oauth2.credentials import exceptions
from googleapiclient.discovery import build

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
        """Get the credentials, try and refresh if needed, and if we can't refresh.
        delete the credentials so we can trigger a re-add."""
        if self.credentials is None:
            return None
        stored_creds = json.loads(self.credentials)
        # Get expirery so we can figure out if we need a refresh
        if self.credential_expiry is not None:
            stored_creds["expiry"] = self.credential_expiry
        else:
            stored_creds["expiry"] = datetime.now()

        # Drop timezone info
        stored_creds["expiry"] = stored_creds["expiry"].replace(tzinfo=None)
        user_credentials = google.oauth2.credentials.Credentials(**stored_creds)
        try:
            if user_credentials.expired:
                http_request = google.auth.transport.requests.Request()
                user_credentials.refresh(http_request)
        except exceptions.RefreshError:
              revoke = requests.post(
                  'https://oauth2.googleapis.com/revoke',
                  params={'token': user_credentials.token},
                  headers = {'content-type': 'application/x-www-form-urlencoded'})
              self.credentials = None
              self.save()
              return None
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

    class Meta:
        app_label = "cal_sync_magic"


class UserCalendar(models.Model):
    def hex_uuid(): # type: ignore
        """Hecking MYSQL hex UUID issue."""
        return uuid.uuid4().hex

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False)
    internal_calendar_id = models.AutoField(primary_key=True)
    google_account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE, null=False)
    google_calendar_id = models.CharField(max_length=500, null=False)
    name = models.CharField(max_length=500, null=True, blank=True)
    last_error = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    last_sync_token = models.CharField(max_length=500, null=True, blank=True)
    webhook_enabled = models.BooleanField(default=False) # See https://developers.google.com/calendar/api/guides/push

    def __str__(self):
        if self.name is None:
            return "None"
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
        calendar_service = self.google_account.calendar_service()p
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

    def make_channel_id(self):
        return f"{self.internal_calendar_id}-{self.google_calendar_id}"

    def subscribe_if_needed(self, address):
        if (!self.webhook_enabled):
            self.webhook_enabled = True
            calendar_service = self.google_account.calendar_service()
            calendar_service.events().watch(
                calendarId = self.google_calendar_id,
                id = self.make_channel_id(),
                address = address
            ).execute()
            self.save()
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
