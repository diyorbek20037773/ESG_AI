from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from src.apps.blog.models import Post
from src.apps.news.models import News

from .forms import ContactForm


def uzc(request):
    """Standalone UzCombinator application landing (own HTML shell, no base.html)."""
    return render(request, 'core/uzc.html')


def index(request):
    order = ['hisobot', 'yangilanish', 'tadbir', 'hamkorlik']
    latest_news = []
    for news_type in order:
        item = (
            News.objects.filter(type=news_type)
            .prefetch_related('images')
            .order_by('-date', '-created_at')
            .first()
        )
        if item:
            latest_news.append(item)

    latest_posts = Post.objects.select_related('author__profile').order_by('-created_at')[:3]

    return render(request, 'core/index.html', {
        'latest_news':   latest_news,
        'latest_posts':  latest_posts,
        'contact_form':  ContactForm(),
        'contact_email': settings.EMAIL_HOST_USER,
    })


@require_POST
def contact_submit(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        contact = form.save()
        send_mail(
            subject=f"[NovdAI] Yangi xabar: {contact.subject or 'Mavzusiz'}",
            message=(
                f"Ism: {contact.name}\n"
                f"Email: {contact.email}\n"
                f"Mavzu: {contact.subject or '—'}\n\n"
                f"Xabar:\n{contact.message}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=True,
        )
        messages.success(request, _("Contact success msg"))
    else:
        messages.error(request, _("Contact error msg"))

    return redirect(reverse('core:index') + '#contact')
