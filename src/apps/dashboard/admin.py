from django.contrib import admin

from .models import Analysis, Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'stir', 'industry', 'region', 'analyses_count', 'created_at')
    search_fields = ('name', 'stir', 'industry', 'region')
    list_filter = ('industry', 'region')


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('number', 'kind', 'created_by', 'client', 'company_name', 'verdict',
                    'overall_score', 'environmental_score', 'social_score',
                    'governance_score', 'language', 'created_at')
    list_filter = ('kind', 'verdict', 'language', 'created_at')
    search_fields = ('number', 'company_name', 'client__name', 'summary',
                     'created_by__username', 'created_by__email')
    readonly_fields = ('created_at', 'result_json')
