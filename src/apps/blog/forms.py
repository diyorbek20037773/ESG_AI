from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import Post


class PostForm(forms.ModelForm):
    body = forms.CharField(
        label='Matn',
        widget=CKEditorUploadingWidget(),
    )

    class Meta:
        model = Post
        fields = ['title', 'featured_image', 'excerpt', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Sarlavha kiriting...',
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control rounded-3',
                'rows': 3,
                'placeholder': 'Qisqa mazmun (ixtiyoriy)...',
            }),
        }
        labels = {
            'title': 'Sarlavha',
            'featured_image': 'Asosiy rasm',
            'excerpt': 'Qisqa matn',
        }
