from django.views.generic import ListView
from ..models import News


class NewsListView(ListView):
    model = News
    template_name = 'news/list.html'
    context_object_name = 'news_list'
    paginate_by = 9

    def get_queryset(self):
        qs = News.objects.prefetch_related('images').order_by('-date', '-created_at')
        news_type = self.request.GET.get('type')
        if news_type:
            qs = qs.filter(type=news_type)
        return qs
