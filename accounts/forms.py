from zoneinfo import available_timezones

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from .models import SavedSearch, UserProfile, VenueList

INPUT = "input"
CHECKBOX = "h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"


class StyledFormMixin:
    """Apply the design-system classes (see frontend/styles.css) to every widget."""

    def _style(self):
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", CHECKBOX)
            elif not isinstance(w, forms.HiddenInput):
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
        fields = ["display_name", "affiliation", "research_interests", "timezone", "email_reminders", "reminder_days", "weekly_digest"]

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


class StyledPasswordResetForm(StyledFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    pass


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class EmailChangeForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label="New email address")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email


class DeleteAccountForm(StyledFormMixin, forms.Form):
    password = forms.CharField(label="Confirm with your password", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    confirm = forms.CharField(label='Type "DELETE" to confirm', max_length=10)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password

    def clean_confirm(self):
        if self.cleaned_data["confirm"].strip() != "DELETE":
            raise forms.ValidationError("Please type DELETE in capital letters.")
        return self.cleaned_data["confirm"]
