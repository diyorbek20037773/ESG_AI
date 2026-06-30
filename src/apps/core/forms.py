from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'maxlength': '150',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control rounded-3',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'maxlength': '200',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control rounded-3',
                'rows': '5',
            }),
        }
