from django.db import models
from django.utils.translation import gettext_lazy as _


class ESGAnalysis(models.Model):
    """One ESG analysis run produced by Gemini over a document or pasted text."""

    SOURCE_FILE = 'file'
    SOURCE_TEXT = 'text'
    SOURCE_CHOICES = [
        (SOURCE_FILE, _('Document')),
        (SOURCE_TEXT, _('Text')),
    ]

    company_name = models.CharField(_('Company name'), max_length=255, blank=True)
    source_type = models.CharField(max_length=8, choices=SOURCE_CHOICES, default=SOURCE_FILE)
    original_filename = models.CharField(max_length=255, blank=True)

    environmental_score = models.PositiveSmallIntegerField(default=0)
    social_score = models.PositiveSmallIntegerField(default=0)
    governance_score = models.PositiveSmallIntegerField(default=0)
    overall_score = models.PositiveSmallIntegerField(default=0)

    summary = models.TextField(blank=True)
    # Full structured Gemini result: pillar summaries, findings, risks, recommendations.
    result_json = models.JSONField(default=dict)
    language = models.CharField(max_length=8, default='uz')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('ESG analysis')
        verbose_name_plural = _('ESG analyses')

    def __str__(self):
        label = self.company_name or self.original_filename or _('Untitled')
        return f'{label} — {self.overall_score}/100'

    @property
    def rating(self):
        """Letter rating derived from the overall score (AAA … CCC scale)."""
        s = self.overall_score
        if s >= 90:
            return 'AAA'
        if s >= 80:
            return 'AA'
        if s >= 70:
            return 'A'
        if s >= 60:
            return 'BBB'
        if s >= 50:
            return 'BB'
        if s >= 40:
            return 'B'
        if s >= 30:
            return 'CCC'
        if s >= 20:
            return 'CC'
        return 'C'
