from django import forms

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

    def get_config_form(self):
        f = UpdateGoogleAccountForm()
        f.fields["account_id"].initial = self.account_id
        f.fields["calendar_sync_enabled"].initial = self.calendar_sync_enabled
        f.fields["second_chance_email"].initial = self.second_chance_email
        f.fields["delete_events_from_email"].initial = self.delete_events_from_email
        return f


    class Meta:
        app_label = "cal_sync_magic"




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
