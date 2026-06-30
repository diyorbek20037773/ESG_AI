from django.contrib import admin

from .models import ESGAnalysis


@admin.register(ESGAnalysis)
class ESGAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'company_name', 'overall_score', 'environmental_score',
        'social_score', 'governance_score', 'language', 'created_at',
    )
    list_filter = ('language', 'source_type', 'created_at')
    search_fields = ('company_name', 'original_filename', 'summary')
    readonly_fields = ('created_at', 'result_json')
