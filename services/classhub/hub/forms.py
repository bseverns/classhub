from __future__ import annotations

from django import forms


class SubmissionUploadForm(forms.Form):
    file = forms.FileField(required=True)
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note for your teacher…"}),
        max_length=2000,
    )
