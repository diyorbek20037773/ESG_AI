from django.db import models


class News(models.Model):
    TYPE_CHOICES = [
        ('tadbir', 'Tadbir'),
        ('yangilanish', 'Yangilanish'),
        ('hisobot', 'Hisobot'),
        ('hamkorlik', 'Hamkorlik'),
    ]

    BADGE_COLORS = {
        'tadbir': 'warning',
        'yangilanish': 'danger',
        'hisobot': 'info',
        'hamkorlik': 'success',
    }

    type = models.CharField('Turi', max_length=20, choices=TYPE_CHOICES)
    title = models.CharField('Sarlavha', max_length=255)
    body = models.TextField('Matn')
    date = models.DateField('Sana')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Yangilik'
        verbose_name_plural = 'news'

    def __str__(self):
        return self.title

    @property
    def badge_color(self):
        return self.BADGE_COLORS.get(self.type, 'secondary')

    @property
    def first_image(self):
        return self.images.order_by('order', 'id').first()


class NewsImage(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Rasm', upload_to='news/')
    order = models.PositiveSmallIntegerField('Tartib', default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Rasm'
        verbose_name_plural = 'Rasmlar'

    def __str__(self):
        return f'{self.news.title} — rasm {self.order}'
