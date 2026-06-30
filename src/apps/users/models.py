from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='profile', verbose_name='Foydalanuvchi'
    )
    avatar = models.ImageField(
        'Rasm', upload_to='users/avatars/', blank=True, null=True
    )
    job_title = models.CharField(
        'Kasbi / lavozimi', max_length=150, blank=True
    )

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profillar'

    def __str__(self):
        return f'{self.user.username} profili'
