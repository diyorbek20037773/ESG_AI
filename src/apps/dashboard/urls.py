from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('history/', views.history, name='history'),
    path('<int:pk>/', views.detail, name='detail'),
]
