from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField

User = get_user_model()


class Post(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='blog_posts', verbose_name='Muallif'
    )
    title = models.CharField('Sarlavha', max_length=255)
    slug = models.SlugField('Slug', max_length=280, unique=True, blank=True)
    featured_image = models.ImageField(
        'Asosiy rasm', upload_to='blog/images/', blank=True, null=True
    )
    excerpt = models.TextField('Qisqa matn', max_length=500, blank=True)
    body = RichTextUploadingField('Matn')
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Postlar'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def view_count(self):
        return self.post_views.count()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title_uz or self.title or '', allow_unicode=True)
            if not base_slug:
                base_slug = 'post'
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class PostView(models.Model):
    """Tracks unique views per user (authenticated) or IP (anonymous)."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_views')
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Foydalanuvchi'
    )
    ip_address = models.GenericIPAddressField('IP manzil', null=True, blank=True)
    viewed_at = models.DateTimeField('Ko\'rilgan vaqt', auto_now_add=True)

    class Meta:
        verbose_name = 'Ko\'rish'
        verbose_name_plural = 'Ko\'rishlar'
