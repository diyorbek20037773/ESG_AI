from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fields = ('avatar', 'job_title')


class UserAdmin(BaseUserAdmin):
    inlines = []
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'get_job_title')

    def get_inlines(self, request, obj=None):
        # Faqat mavjud userni tahrirlashda profil inline ko'rinadi
        if obj is not None:
            return [ProfileInline]
        return []

    def get_job_title(self, obj):
        try:
            return obj.profile.job_title or '—'
        except Profile.DoesNotExist:
            return '—'
    get_job_title.short_description = 'Kasbi'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            Profile.objects.get_or_create(user=obj)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
