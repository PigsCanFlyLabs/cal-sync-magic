from django import forms
from django.core.validators import RegexValidator

from cal_sync_magic.models import CalendarRules, SyncConfigs


# We use a regular form instead of model form because we want the account id (e.g. two users _could_ add the same google account
# so this way we know were modifying the correct users google account).
class UpdateGoogleAccountForm(forms.Form):
    account_id = forms.CharField(label='Account ID', max_length=200, required=True, widget=forms.HiddenInput)
    calendar_sync_enabled = forms.BooleanField(label="Calendar Sync", required=False)
    second_chance_email = forms.BooleanField(label="2nd chance e-mail", required=False)
    delete_events_from_email = forms.BooleanField(label="Delete events based on email", required=False)


class NewSyncForm(forms.ModelForm):
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


class NewCalRuleForm(forms.ModelForm):
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

__all__ = ["NewCalRuleForm", "NewSyncForm", "UpdateGoogleAccountForm"]
