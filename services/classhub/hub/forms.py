from django import forms
from django.utils.translation import gettext_lazy as _


class SubmissionUploadForm(forms.Form):
    file = forms.FileField(required=True)
    station_label = forms.CharField(
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs={"placeholder": _("Optional station")}),
    )
    process_note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": _("What did you try? What did you change? (optional)")}
        ),
        max_length=2000,
    )
    note = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        max_length=2000,
    )
