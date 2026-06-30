from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Post, PostView


@admin.register(Post)
class PostAdmin(TranslationAdmin):
    list_display = ('title', 'author', 'view_count', 'created_at')
    search_fields = ('title', 'excerpt')
    prepopulated_fields = {'slug': ('title_uz',)}
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        ('Asosiy', {
            'fields': ('title', 'slug', 'author')
        }),
        ('Kontent', {
            'fields': ('featured_image', 'excerpt', 'body')
        }),
        ('Ma\'lumot', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'ip_address', 'viewed_at')
    list_filter = ('post',)
    readonly_fields = ('post', 'user', 'ip_address', 'viewed_at')
