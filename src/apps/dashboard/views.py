import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from . import ai_service
from .forms import ALLOWED_MIME, ESGAnalysisForm
from .models import ESGAnalysis

logger = logging.getLogger(__name__)


def index(request):
    """ESG dashboard: upload a document / paste text, run AI analysis, show result."""
    analysis = None
    form = ESGAnalysisForm()
    recent = ESGAnalysis.objects.all()[:5]

    if request.method == 'POST':
        form = ESGAnalysisForm(request.POST, request.FILES)
        if not ai_service._get_api_keys():
            messages.error(request, _('AI engine is not configured.'))
        elif form.is_valid():
            company = form.cleaned_data['company_name'].strip()
            document = form.cleaned_data.get('document')
            text = (form.cleaned_data.get('text') or '').strip()
            language = get_language() or 'uz'

            try:
                if document:
                    mime = ALLOWED_MIME.get(
                        document.content_type, document.content_type or 'application/pdf')
                    result = ai_service.analyze_esg(
                        file_bytes=document.read(),
                        file_mime=mime,
                        company_name=company,
                        language=language,
                    )
                    source_type = ESGAnalysis.SOURCE_FILE
                    filename = document.name
                else:
                    result = ai_service.analyze_esg(
                        text=text,
                        company_name=company,
                        language=language,
                    )
                    source_type = ESGAnalysis.SOURCE_TEXT
                    filename = ''

                analysis = ESGAnalysis.objects.create(
                    company_name=result['company_name'] or company,
                    source_type=source_type,
                    original_filename=filename,
                    environmental_score=result['environmental_score'],
                    social_score=result['social_score'],
                    governance_score=result['governance_score'],
                    overall_score=result['overall_score'],
                    summary=result['overall_summary'],
                    result_json=result,
                    language=language,
                )
                messages.success(request, _('Analysis complete.'))
            except Exception as e:  # noqa: BLE001 — surface a friendly message
                logger.exception('ESG analysis failed')
                messages.error(
                    request,
                    _('Analysis failed: %(err)s') % {'err': str(e)[:200]},
                )

    return render(request, 'dashboard/index.html', {
        'form': form,
        'analysis': analysis,
        'recent': recent,
    })


def history(request):
    analyses = ESGAnalysis.objects.all()[:100]
    return render(request, 'dashboard/history.html', {'analyses': analyses})


def detail(request, pk):
    analysis = get_object_or_404(ESGAnalysis, pk=pk)
    return render(request, 'dashboard/detail.html', {'analysis': analysis})
