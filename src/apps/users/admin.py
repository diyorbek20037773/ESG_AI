from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import LoginEvent, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fields = ('role', 'avatar', 'job_title')


class UserAdmin(BaseUserAdmin):
    inlines = []
    list_display = ('username', 'email', 'get_role', 'is_active', 'is_staff',
                    'date_joined', 'last_login', 'get_analyses')
    list_filter = BaseUserAdmin.list_filter + ('profile__role',)

    def get_inlines(self, request, obj=None):
        # Faqat mavjud userni tahrirlashda profil inline ko'rinadi
        if obj is not None:
            return [ProfileInline]
        return []

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Profile.DoesNotExist:
            return '—'
    get_role.short_description = 'Rol'

    def get_analyses(self, obj):
        return obj.analyses.count()
    get_analyses.short_description = 'Tahlillar'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            Profile.objects.get_or_create(user=obj)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'ip')
    readonly_fields = ('user', 'ip', 'user_agent', 'created_at')
    date_hierarchy = 'created_at'
