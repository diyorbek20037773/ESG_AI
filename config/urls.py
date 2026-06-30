"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += [
    path('ckeditor/', include('ckeditor_uploader.urls')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('src.apps.core.urls', namespace='core')),
    path('dashboard/', include('src.apps.dashboard.urls', namespace='dashboard')),
    path('yangiliklar/', include('src.apps.news.urls', namespace='news')),
    path('blog/', include('src.apps.blog.urls', namespace='blog')),
    path('', include('src.apps.users.urls', namespace='users')),
    prefix_default_language=False,
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
