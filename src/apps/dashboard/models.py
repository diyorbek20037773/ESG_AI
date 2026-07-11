from django.db import models
from django.utils.translation import gettext_lazy as _

from . import constants


class Client(models.Model):
    """A bank client / borrower whose green-finance projects are analysed."""

    name = models.CharField(_('Client name'), max_length=255)
    stir = models.CharField(_('Tax ID (STIR)'), max_length=32, blank=True)
    industry = models.CharField(_('Industry'), max_length=128, blank=True)
    region = models.CharField(_('Region'), max_length=128, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def __str__(self):
        return self.name

    @property
    def analyses_count(self):
        return self.analyses.count()

    @property
    def latest_analysis(self):
        return self.analyses.order_by('-created_at').first()


class Analysis(models.Model):
    """One green-finance ESG analysis run over a client's project documents."""

    SOURCE_FILE = 'file'
    SOURCE_TEXT = 'text'
    SOURCE_CHOICES = [(SOURCE_FILE, _('Document')), (SOURCE_TEXT, _('Text'))]

    VERDICT_CHOICES = [
        (constants.VERDICT_GREEN, _('Green')),
        (constants.VERDICT_NOT_GREEN, _('Not green')),
        (constants.VERDICT_UNKNOWN, _('Unknown')),
    ]

    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='analyses', verbose_name=_('Client'),
    )
    number = models.CharField(max_length=16, unique=True, db_index=True)
    company_name = models.CharField(_('Company name'), max_length=255, blank=True)

    source_type = models.CharField(max_length=8, choices=SOURCE_CHOICES, default=SOURCE_FILE)
    filenames = models.JSONField(default=list, blank=True)

    verdict = models.CharField(max_length=12, choices=VERDICT_CHOICES,
                               default=constants.VERDICT_UNKNOWN, db_index=True)
    verdict_title = models.CharField(max_length=128, blank=True)
    summary = models.TextField(blank=True)

    environmental_score = models.PositiveSmallIntegerField(default=0)
    social_score = models.PositiveSmallIntegerField(default=0)
    governance_score = models.PositiveSmallIntegerField(default=0)
    overall_score = models.PositiveSmallIntegerField(default=0)

    # Full structured result: info answers, eco expertise, stop factors, green criteria.
    result_json = models.JSONField(default=dict)
    language = models.CharField(max_length=8, default='uz')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Analysis')
        verbose_name_plural = _('Analyses')

    def __str__(self):
        label = self.company_name or (self.client.name if self.client else '') or self.number
        return f'{self.number} — {label}'

    @property
    def rating(self):
        """Letter rating from the overall score (AAA … C)."""
        s = self.overall_score
        thresholds = [(90, 'AAA'), (80, 'AA'), (70, 'A'), (60, 'BBB'),
                      (50, 'BB'), (40, 'B'), (30, 'CCC'), (20, 'CC')]
        for cutoff, label in thresholds:
            if s >= cutoff:
                return label
        return 'C'

    @property
    def is_green(self):
        return self.verdict == constants.VERDICT_GREEN

    @property
    def verdict_color(self):
        """Semantic color token name for the verdict (used by templates)."""
        return {
            constants.VERDICT_GREEN: 'approved',
            constants.VERDICT_NOT_GREEN: 'rejected',
            constants.VERDICT_UNKNOWN: 'unknown',
        }.get(self.verdict, 'unknown')

    @property
    def stop_factors(self):
        return self.result_json.get('stop_factors', []) if isinstance(self.result_json, dict) else []

    @property
    def green_criteria(self):
        return self.result_json.get('green_criteria', []) if isinstance(self.result_json, dict) else []

    @property
    def info_answers(self):
        return self.result_json.get('info', []) if isinstance(self.result_json, dict) else []

    @property
    def triggered_stops(self):
        return [s for s in self.stop_factors if s.get('value')]

    @property
    def matched_green(self):
        return [g for g in self.green_criteria if g.get('value')]
