import logging
import os

from django.contrib import messages
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from . import ai_service, constants, pdf_service
from .forms import ALLOWED_EXT, ALLOWED_MIME, MAX_FILE_MB, MAX_FILES, GreenFinanceForm
from .models import Analysis, Client

logger = logging.getLogger(__name__)


def _gen_number():
    last = Analysis.objects.order_by('-id').first()
    seq = (last.id if last else 0) + 1
    return f"2026{seq:05d}"


def _dashboard_stats():
    qs = Analysis.objects.all()
    total = qs.count()
    green = qs.filter(verdict=constants.VERDICT_GREEN).count()
    not_green = qs.filter(verdict=constants.VERDICT_NOT_GREEN).count()
    unknown = qs.filter(verdict=constants.VERDICT_UNKNOWN).count()
    agg = qs.aggregate(e=Avg('environmental_score'), s=Avg('social_score'),
                       g=Avg('governance_score'), o=Avg('overall_score'))
    return {
        'total': total,
        'green': green, 'not_green': not_green, 'unknown': unknown,
        'green_rate': round(green / total * 100) if total else 0,
        'clients': Client.objects.count(),
        'avg_e': round(agg['e'] or 0), 'avg_s': round(agg['s'] or 0),
        'avg_g': round(agg['g'] or 0), 'avg_overall': round(agg['o'] or 0),
    }


def home(request):
    stats = _dashboard_stats()
    recent = Analysis.objects.select_related('client')[:6]
    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'recent': recent,
        'verdict_max': max(stats['green'], stats['not_green'], stats['unknown'], 1),
    })


def analyses(request):
    items = Analysis.objects.select_related('client')[:200]
    return render(request, 'dashboard/analyses.html', {'analyses': items})


def clients(request):
    items = Client.objects.annotate(n=Count('analyses')).order_by('name')
    return render(request, 'dashboard/clients.html', {'clients': items})


def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'dashboard/client_detail.html', {
        'client': client,
        'analyses': client.analyses.all(),
    })


def new_analysis(request):
    form = GreenFinanceForm()
    if request.method == 'POST':
        form = GreenFinanceForm(request.POST, request.FILES)
        uploads = request.FILES.getlist('documents')
        if not ai_service._get_api_keys():
            messages.error(request, _('AI engine is not configured.'))
        elif form.is_valid():
            files, filenames, bad = [], [], False
            for f in uploads[:MAX_FILES]:
                name = (f.name or '').lower()
                if not name.endswith(ALLOWED_EXT):
                    messages.error(request, _('Unsupported file type. Use PDF, PNG, JPG or WEBP.'))
                    bad = True
                    break
                if f.size > MAX_FILE_MB * 1024 * 1024:
                    messages.error(request, _('File is too large (max 20 MB).'))
                    bad = True
                    break
                mime = ALLOWED_MIME.get(f.content_type, f.content_type or 'application/pdf')
                files.append((f.read(), mime))
                filenames.append(f.name)

            text = (form.cleaned_data.get('text') or '').strip()
            if not bad and not files and not text:
                messages.error(request, _('Upload a document or paste some text to analyse.'))
            elif not bad:
                # Resolve client (existing or new)
                client = form.cleaned_data.get('client')
                new_name = form.cleaned_data.get('new_client')
                if not client and new_name:
                    client = Client.objects.create(name=new_name)

                language = get_language() or 'uz'
                try:
                    result = ai_service.analyze_green_finance(
                        files=files or None, text=text or None,
                        client_name=client.name if client else '', language=language,
                    )
                    analysis = Analysis.objects.create(
                        client=client,
                        number=_gen_number(),
                        company_name=result['company_name'],
                        source_type=Analysis.SOURCE_FILE if files else Analysis.SOURCE_TEXT,
                        filenames=filenames,
                        verdict=result['verdict']['code'],
                        verdict_title=result['verdict']['title'],
                        summary=result['summary'],
                        environmental_score=result['environmental_score'],
                        social_score=result['social_score'],
                        governance_score=result['governance_score'],
                        overall_score=result['overall_score'],
                        result_json={
                            'info': result['info'],
                            'eco_required': result['eco_required'],
                            'eco_obtained': result['eco_obtained'],
                            'stop_factors': result['stop_factors'],
                            'green_criteria': result['green_criteria'],
                            'verdict': result['verdict'],
                        },
                        language=language,
                    )
                    messages.success(request, _('Analysis complete.'))
                    return redirect('dashboard:analysis_detail', pk=analysis.pk)
                except Exception as e:  # noqa: BLE001
                    logger.exception('green-finance analysis failed')
                    messages.error(request, _('Analysis failed: %(err)s') % {'err': str(e)[:200]})

    return render(request, 'dashboard/new_analysis.html', {'form': form})


def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis.objects.select_related('client'), pk=pk)
    return render(request, 'dashboard/analysis_detail.html', {'analysis': analysis})


def download_pdf(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk)
    pdf = pdf_service.build_verdict_pdf(analysis)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="NovdAI_ESG_{analysis.number}.pdf"'
    return resp


def analytics(request):
    stats = _dashboard_stats()
    by_industry = (Client.objects.values('industry')
                   .annotate(n=Count('analyses')).order_by('-n')[:8])
    return render(request, 'dashboard/analytics.html', {
        'stats': stats,
        'by_industry': by_industry,
        'verdict_max': max(stats['green'], stats['not_green'], stats['unknown'], 1),
    })
