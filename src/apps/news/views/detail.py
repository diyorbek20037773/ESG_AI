from django.views.generic import DetailView
from ..models import News


class NewsDetailView(DetailView):
    model = News
    template_name = 'news/detail.html'
    context_object_name = 'news'
