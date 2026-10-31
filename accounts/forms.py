from zoneinfo import available_timezones

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import SavedSearch, UserProfile, VenueList

INPUT = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"


class StyledFormMixin:
    def _style(self):
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "rounded border-slate-300")
            else:
                w.attrs["class"] = INPUT
                if isinstance(w, forms.Textarea):
                    w.attrs.setdefault("rows", 3)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


class SignUpForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class StyledAuthForm(StyledFormMixin, AuthenticationForm):
    pass


class ProfileForm(StyledFormMixin, forms.ModelForm):
    timezone = forms.ChoiceField(choices=[(t, t) for t in sorted(available_timezones())])

    class Meta:
        model = UserProfile
        fields = ["display_name", "affiliation", "research_interests", "timezone", "email_reminders", "reminder_days"]

    def clean_reminder_days(self):
        raw = self.cleaned_data["reminder_days"]
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts or not all(p.isdigit() and 0 < int(p) <= 365 for p in parts):
            raise forms.ValidationError("Enter comma-separated day counts between 1 and 365, e.g. 14,7,1")
        return ",".join(parts)


class VenueListForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = VenueList
        fields = ["name", "description", "is_public"]


class SavedSearchForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ["name", "querystring", "alert"]
        widgets = {"querystring": forms.HiddenInput()}
