from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from .models import ROLE_CHOICES, ROLE_BANK

User = get_user_model()


class RegisterForm(forms.Form):
    """Open self-registration. Email is used as the username."""
    full_name = forms.CharField(
        label=_('Full name'), max_length=150, required=False
    )
    email = forms.EmailField(label=_('Email'))
    role = forms.ChoiceField(
        label=_('Account type'), choices=ROLE_CHOICES, initial=ROLE_BANK,
        widget=forms.RadioSelect,
    )
    password1 = forms.CharField(label=_('Password'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Confirm password'), widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('An account with this email already exists.'))
        return email

    def clean_password1(self):
        pw = self.cleaned_data.get('password1', '')
        validate_password(pw)
        return pw

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _('Passwords do not match.'))
        return cleaned

    def save(self):
        email = self.cleaned_data['email']
        user = User.objects.create_user(
            username=email, email=email, password=self.cleaned_data['password1'],
        )
        full = (self.cleaned_data.get('full_name') or '').strip()
        if full:
            parts = full.split(None, 1)
            user.first_name = parts[0][:150]
            if len(parts) > 1:
                user.last_name = parts[1][:150]
            user.save(update_fields=['first_name', 'last_name'])
        # Profile with chosen role
        from .models import Profile
        Profile.objects.update_or_create(
            user=user, defaults={'role': self.cleaned_data['role']}
        )
        return user
