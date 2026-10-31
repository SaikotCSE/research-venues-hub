from django import forms

from accounts.forms import StyledFormMixin

from .models import DeadlineSuggestion, VenueReview


class ReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = VenueReview
        fields = ["rating", "review_quality", "turnaround_days", "outcome", "comment"]


class SuggestionForm(StyledFormMixin, forms.ModelForm):
    new_value = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), label="New value (UTC)")

    source_url = forms.URLField(required=False, assume_scheme="https", label="Source URL")

    class Meta:
        model = DeadlineSuggestion
        fields = ["field", "new_value", "source_url", "note"]
