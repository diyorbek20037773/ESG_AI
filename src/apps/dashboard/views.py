import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
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


def _is_entrepreneur(user):
    return (user.is_authenticated
            and hasattr(user, 'profile') and user.profile.is_entrepreneur
            and not user.is_superuser)


def _bank_analyses(request):
    """Bank verdict runs. Anonymous + bank users see all bank analyses;
    superuser sees all. (Entrepreneur readiness runs are excluded.)"""
    return Analysis.objects.filter(kind=Analysis.KIND_BANK)


def _my_readiness(request):
    """An entrepreneur's own readiness runs."""
    qs = Analysis.objects.filter(kind=Analysis.KIND_READINESS)
    if request.user.is_authenticated and not request.user.is_superuser:
        qs = qs.filter(created_by=request.user)
    return qs


def _dashboard_stats(qs):
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
    # Entrepreneurs get their readiness home instead of the bank overview.
    if _is_entrepreneur(request.user):
        return redirect('dashboard:readiness')
    bank = _bank_analyses(request)
    stats = _dashboard_stats(bank)
    recent = bank.select_related('client')[:6]
    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'recent': recent,
        'verdict_max': max(stats['green'], stats['not_green'], stats['unknown'], 1),
    })


def analyses(request):
    items = _bank_analyses(request).select_related('client')[:200]
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


def _read_uploads(request):
    """Return (files, filenames, error_msg_or_None) from request.FILES['documents']."""
    files, filenames = [], []
    for f in request.FILES.getlist('documents')[:MAX_FILES]:
        name = (f.name or '').lower()
        if not name.endswith(ALLOWED_EXT):
            return None, None, _('Unsupported file type. Use PDF, PNG, JPG or WEBP.')
        if f.size > MAX_FILE_MB * 1024 * 1024:
            return None, None, _('File is too large (max 20 MB).')
        mime = ALLOWED_MIME.get(f.content_type, f.content_type or 'application/pdf')
        files.append((f.read(), mime))
        filenames.append(f.name)
    return files, filenames, None


def _run_analysis(*, files, filenames, text, client, kind, user, language):
    """Shared extraction + persistence for both bank and readiness flows."""
    result = ai_service.analyze_green_finance(
        files=files or None, text=text or None,
        client_name=client.name if client else '', language=language,
    )
    return Analysis.objects.create(
        kind=kind,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
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


@login_required
def new_analysis(request):
    form = GreenFinanceForm()
    if request.method == 'POST':
        form = GreenFinanceForm(request.POST, request.FILES)
        if not ai_service._get_api_keys():
            messages.error(request, _('AI engine is not configured.'))
        elif form.is_valid():
            files, filenames, err = _read_uploads(request)
            text = (form.cleaned_data.get('text') or '').strip()
            if err:
                messages.error(request, err)
            elif not files and not text:
                messages.error(request, _('Upload a document or paste some text to analyse.'))
            else:
                client = form.cleaned_data.get('client')
                new_name = form.cleaned_data.get('new_client')
                if not client and new_name:
                    client = Client.objects.create(name=new_name, created_by=request.user)
                language = get_language() or 'uz'
                try:
                    analysis = _run_analysis(
                        files=files, filenames=filenames, text=text, client=client,
                        kind=Analysis.KIND_BANK, user=request.user, language=language,
                    )
                    messages.success(request, _('Analysis complete.'))
                    return redirect('dashboard:analysis_detail', pk=analysis.pk)
                except Exception as e:  # noqa: BLE001
                    logger.exception('green-finance analysis failed')
                    messages.error(request, _('Analysis failed: %(err)s') % {'err': str(e)[:200]})

    return render(request, 'dashboard/new_analysis.html', {'form': form})


def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis.objects.select_related('client'), pk=pk)
    # Readiness runs are private to their owner (+ superuser).
    if (analysis.kind == Analysis.KIND_READINESS and not request.user.is_superuser
            and analysis.created_by_id != getattr(request.user, 'id', None)):
        return redirect('dashboard:index')
    return render(request, 'dashboard/analysis_detail.html', {'analysis': analysis})


def download_pdf(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk)
    pdf = pdf_service.build_verdict_pdf(analysis)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="NovdAI_ESG_{analysis.number}.pdf"'
    return resp


def analytics(request):
    bank = _bank_analyses(request)
    stats = _dashboard_stats(bank)
    by_industry = (Client.objects.values('industry')
                   .annotate(n=Count('analyses')).order_by('-n')[:8])
    return render(request, 'dashboard/analytics.html', {
        'stats': stats,
        'by_industry': by_industry,
        'verdict_max': max(stats['green'], stats['not_green'], stats['unknown'], 1),
    })


# ── Entrepreneur readiness ───────────────────────────────────────────────
def readiness(request):
    """Entrepreneur self-check: upload a project → readiness speedometer."""
    form = GreenFinanceForm()
    latest = None
    if request.user.is_authenticated:
        latest = _my_readiness(request).first()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{request.build_absolute_uri('/login/')}?next={request.path}")
        form = GreenFinanceForm(request.POST, request.FILES)
        if not ai_service._get_api_keys():
            messages.error(request, _('AI engine is not configured.'))
        elif form.is_valid():
            files, filenames, err = _read_uploads(request)
            text = (form.cleaned_data.get('text') or '').strip()
            if err:
                messages.error(request, err)
            elif not files and not text:
                messages.error(request, _('Upload a document or paste some text to analyse.'))
            else:
                language = get_language() or 'uz'
                try:
                    analysis = _run_analysis(
                        files=files, filenames=filenames, text=text, client=None,
                        kind=Analysis.KIND_READINESS, user=request.user, language=language,
                    )
                    messages.success(request, _('Readiness check complete.'))
                    return redirect('dashboard:readiness_detail', pk=analysis.pk)
                except Exception as e:  # noqa: BLE001
                    logger.exception('readiness check failed')
                    messages.error(request, _('Analysis failed: %(err)s') % {'err': str(e)[:200]})

    return render(request, 'dashboard/readiness.html', {'form': form, 'latest': latest})


def readiness_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk, kind=Analysis.KIND_READINESS)
    if not request.user.is_superuser and analysis.created_by_id != getattr(request.user, 'id', None):
        return redirect('dashboard:readiness')
    return render(request, 'dashboard/readiness_detail.html', {'a': analysis})


@login_required
def my_checks(request):
    items = _my_readiness(request).order_by('-created_at')[:200]
    return render(request, 'dashboard/my_checks.html', {'checks': items})


# ── Admin insights (superuser only, themed) ──────────────────────────────
@user_passes_test(lambda u: u.is_superuser)
def admin_insights(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    users = User.objects.all()
    total_users = users.count()
    bank_users = User.objects.filter(profile__role='bank').count()
    ent_users = User.objects.filter(profile__role='entrepreneur').count()

    all_an = Analysis.objects.all()
    bank_an = all_an.filter(kind=Analysis.KIND_BANK).count()
    read_an = all_an.filter(kind=Analysis.KIND_READINESS).count()

    # registrations per day (last 14)
    reg = (users.annotate(d=TruncDate('date_joined')).values('d')
           .annotate(n=Count('id')).order_by('-d')[:14])
    reg = list(reversed(list(reg)))
    reg_max = max([r['n'] for r in reg], default=1)

    # top users by activity
    top_users = (User.objects.annotate(n=Count('analyses'))
                 .filter(n__gt=0).order_by('-n')[:10])

    # recent uploads (who uploaded what)
    recent = (Analysis.objects.select_related('client', 'created_by')
              .order_by('-created_at')[:20])

    try:
        from src.apps.users.models import LoginEvent
        logins_total = LoginEvent.objects.count()
        recent_logins = LoginEvent.objects.select_related('user')[:12]
    except Exception:
        logins_total, recent_logins = 0, []

    return render(request, 'dashboard/admin_insights.html', {
        'total_users': total_users, 'bank_users': bank_users, 'ent_users': ent_users,
        'total_analyses': all_an.count(), 'bank_an': bank_an, 'read_an': read_an,
        'reg': reg, 'reg_max': reg_max, 'top_users': top_users,
        'recent': recent, 'logins_total': logins_total, 'recent_logins': recent_logins,
    })
