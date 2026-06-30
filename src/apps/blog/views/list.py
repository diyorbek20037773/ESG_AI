from django.views.generic import ListView
from ..models import Post


class BlogListView(ListView):
    model = Post
    template_name = 'blog/list.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        return Post.objects.select_related('author').prefetch_related('post_views')
