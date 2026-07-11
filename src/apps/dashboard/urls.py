from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='index'),
    path('analyses/', views.analyses, name='analyses'),
    path('new/', views.new_analysis, name='new'),
    path('analysis/<int:pk>/', views.analysis_detail, name='analysis_detail'),
    path('analysis/<int:pk>/pdf/', views.download_pdf, name='download_pdf'),
    path('clients/', views.clients, name='clients'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('analytics/', views.analytics, name='analytics'),
]
