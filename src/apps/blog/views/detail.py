from django.views.generic import DetailView
from ..models import Post, PostView


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


class BlogDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Post.objects.select_related('author__profile').prefetch_related('post_views')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self._track_view(obj)
        return obj

    def _track_view(self, post):
        if self.request.user.is_authenticated:
            PostView.objects.get_or_create(post=post, user=self.request.user)
        else:
            ip = _get_client_ip(self.request)
            if ip and not PostView.objects.filter(post=post, user=None, ip_address=ip).exists():
                PostView.objects.create(post=post, ip_address=ip)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related_posts'] = Post.objects.exclude(
            pk=self.object.pk
        ).select_related('author__profile').order_by('-created_at')[:3]
        return ctx
