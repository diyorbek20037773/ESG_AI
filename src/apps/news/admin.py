from django.contrib import admin
from .models import News, NewsImage


class NewsImageInline(admin.TabularInline):
    model = NewsImage
    extra = 1
    fields = ['image', 'order']


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'date', 'created_at']
    list_filter = ['type', 'date']
    search_fields = ['title', 'body']
    inlines = [NewsImageInline]
    date_hierarchy = 'date'
