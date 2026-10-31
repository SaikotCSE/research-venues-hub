from django import forms

from accounts.forms import StyledFormMixin
from venues.models import DeadlineCycle, Venue

from .models import Paper, Submission


class PaperForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Paper
        fields = ["title", "abstract", "keywords"]


class SubmissionForm(StyledFormMixin, forms.ModelForm):
    new_paper_title = forms.CharField(required=False, max_length=250, label="…or create a new paper (title)")

    class Meta:
        model = Submission
        fields = ["paper", "new_paper_title", "venue", "cycle", "status", "submitted_on", "decision_on", "notes"]
        widgets = {"submitted_on": forms.DateInput(attrs={"type": "date"}), "decision_on": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kw):
        super().__init__(*args, **kw)
        self.user = user
        self.fields["paper"].queryset = Paper.objects.filter(user=user)
        self.fields["paper"].required = False
        self.fields["venue"].queryset = Venue.objects.order_by("acronym")
        self.fields["cycle"].queryset = DeadlineCycle.objects.select_related("venue").order_by("venue__acronym", "-year")
        self.fields["cycle"].required = False
        self._style()

    def clean(self):
        data = super().clean()
        if not data.get("paper") and not data.get("new_paper_title"):
            raise forms.ValidationError("Choose an existing paper or enter a title for a new one.")
        cycle, venue = data.get("cycle"), data.get("venue")
        if cycle and venue and cycle.venue_id != venue.id:
            self.add_error("cycle", "This cycle belongs to a different venue.")
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.user = self.user
        if not self.cleaned_data.get("paper"):
            obj.paper = Paper.objects.create(user=self.user, title=self.cleaned_data["new_paper_title"])
        if commit:
            obj.save()
        return obj
