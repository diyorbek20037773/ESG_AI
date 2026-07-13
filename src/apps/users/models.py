from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

ROLE_BANK = 'bank'
ROLE_ENTREPRENEUR = 'entrepreneur'
ROLE_CHOICES = [
    (ROLE_BANK, 'Bank xodimi'),
    (ROLE_ENTREPRENEUR, 'Tadbirkor'),
]


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='profile', verbose_name='Foydalanuvchi'
    )
    role = models.CharField(
        'Rol', max_length=16, choices=ROLE_CHOICES, default=ROLE_BANK, db_index=True
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

    @property
    def is_bank(self):
        return self.role == ROLE_BANK

    @property
    def is_entrepreneur(self):
        return self.role == ROLE_ENTREPRENEUR


class LoginEvent(models.Model):
    """Lightweight audit trail: who logged in, when, from where."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='login_events',
        verbose_name='Foydalanuvchi',
    )
    ip = models.GenericIPAddressField('IP', null=True, blank=True)
    user_agent = models.CharField('Brauzer', max_length=300, blank=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Kirish hodisasi'
        verbose_name_plural = 'Kirish hodisalari'

    def __str__(self):
        return f'{self.user} @ {self.created_at:%Y-%m-%d %H:%M}'
