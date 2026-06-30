from django import forms
from django.utils.translation import gettext_lazy as _

ALLOWED_MIME = {
    'application/pdf': 'application/pdf',
    'image/png': 'image/png',
    'image/jpeg': 'image/jpeg',
    'image/jpg': 'image/jpeg',
    'image/webp': 'image/webp',
}
ALLOWED_EXT = ('.pdf', '.png', '.jpg', '.jpeg', '.webp')
MAX_FILE_MB = 20


class ESGAnalysisForm(forms.Form):
    company_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': _('Company name (optional)'),
        }),
    )
    document = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.png,.jpg,.jpeg,.webp',
        }),
    )
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('Or paste the report / company information here...'),
        }),
    )

    def clean_document(self):
        f = self.cleaned_data.get('document')
        if not f:
            return f
        name = (f.name or '').lower()
        if not name.endswith(ALLOWED_EXT):
            raise forms.ValidationError(_('Unsupported file type. Use PDF, PNG, JPG or WEBP.'))
        if f.size > MAX_FILE_MB * 1024 * 1024:
            raise forms.ValidationError(_('File is too large (max 20 MB).'))
        return f

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('document') and not (cleaned.get('text') or '').strip():
            raise forms.ValidationError(_('Upload a document or paste some text to analyse.'))
        return cleaned
