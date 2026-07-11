from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Client

ALLOWED_MIME = {
    'application/pdf': 'application/pdf',
    'image/png': 'image/png',
    'image/jpeg': 'image/jpeg',
    'image/jpg': 'image/jpeg',
    'image/webp': 'image/webp',
}
ALLOWED_EXT = ('.pdf', '.png', '.jpg', '.jpeg', '.webp')
MAX_FILE_MB = 20
MAX_FILES = 10


class GreenFinanceForm(forms.Form):
    """Kick off a green-finance analysis: pick/create a client, upload docs or paste text.

    Uploaded files are read in the view via ``request.FILES.getlist('documents')``.
    """
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(), required=False,
        empty_label=_('— No client —'),
        widget=forms.Select(attrs={'class': 'nv-input'}),
    )
    new_client = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'nv-input',
                                      'placeholder': _('or add a new client')}),
    )
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'nv-input', 'rows': 7,
                                     'placeholder': _('Or paste the project / credit information here...')}),
    )

    def clean_new_client(self):
        return (self.cleaned_data.get('new_client') or '').strip()
