from django.urls import path
from .views import BlogListView, BlogDetailView, BlogCreateView

app_name = 'blog'

urlpatterns = [
    path('', BlogListView.as_view(), name='list'),
    path('yangi/', BlogCreateView.as_view(), name='create'),
    path('<slug:slug>/', BlogDetailView.as_view(), name='detail'),
]
