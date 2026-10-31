from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

AOE_OFFSET = timedelta(hours=-12)


class ResearchSubfield(models.Model):
    """A research subfield / topic tag (e.g. 'Computer Vision')."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "research subfield"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Venue(models.Model):
    class VenueType(models.TextChoices):
        CONFERENCE = "Conference", "Conference"
        JOURNAL = "Journal", "Journal"
        WORKSHOP = "Workshop/Symposium", "Workshop/Symposium"

    class CoreRank(models.TextChoices):
        A_STAR = "A*", "A*"
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        UNRANKED = "Unranked", "Unranked"

    class CcfRank(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        UNRANKED = "Unranked", "Unranked"

    class Quartile(models.TextChoices):
        Q1 = "Q1", "Q1"
        Q2 = "Q2", "Q2"
        Q3 = "Q3", "Q3"
        Q4 = "Q4", "Q4"

    class AttendanceMode(models.TextChoices):
        IN_PERSON = "In-Person", "In-Person"
        HYBRID = "Hybrid", "Hybrid"
        VIRTUAL = "Virtual", "Virtual"

    class ReviewProcess(models.TextChoices):
        DOUBLE_BLIND = "Double-Blind", "Double-Blind"
        SINGLE_BLIND = "Single-Blind", "Single-Blind"
        OPEN = "Open Peer Review", "Open Peer Review"

    # (a) identity
    name = models.CharField(max_length=200)
    acronym = models.CharField(max_length=40, db_index=True)
    slug = models.SlugField(max_length=80, unique=True)
    venue_type = models.CharField(max_length=24, choices=VenueType.choices, db_index=True)

    # (b) description / scope
    description = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    primary_domain = models.CharField(max_length=80, db_index=True)
    subfields = models.ManyToManyField(ResearchSubfield, related_name="venues", blank=True)

    # (c) conference ranks / metrics
    core_rank = models.CharField(max_length=10, choices=CoreRank.choices, default=CoreRank.UNRANKED, db_index=True)
    ccf_rank = models.CharField(max_length=10, choices=CcfRank.choices, default=CcfRank.UNRANKED, db_index=True)
    h5_index = models.PositiveIntegerField(null=True, blank=True)
    h5_median = models.PositiveIntegerField(null=True, blank=True)

    # (d) journal metrics
    impact_factor = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, db_index=True)
    quartile = models.CharField(max_length=2, choices=Quartile.choices, blank=True, db_index=True)
    citescore = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    sjr = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    issn = models.CharField(max_length=20, blank=True)

    # (e) rolling flag (dated milestones live in DeadlineCycle)
    is_rolling_submission = models.BooleanField(default=False, db_index=True)

    # (f) location
    city = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True, db_index=True)
    continent = models.CharField(max_length=30, blank=True, db_index=True)
    country_flag_emoji = models.CharField(max_length=16, blank=True)
    attendance_mode = models.CharField(max_length=12, choices=AttendanceMode.choices, default=AttendanceMode.IN_PERSON)

    # (g) formatting & submission guidelines
    page_limit = models.CharField(max_length=80, blank=True, help_text="e.g. '9 pages + references'")
    formatting_style = models.CharField(max_length=80, blank=True)
    template_url = models.URLField(max_length=300, blank=True)
    review_process = models.CharField(max_length=20, choices=ReviewProcess.choices, default=ReviewProcess.SINGLE_BLIND, db_index=True)
    is_open_access = models.BooleanField(default=False, db_index=True)
    apc_cost_usd = models.PositiveIntegerField(null=True, blank=True, help_text="Article processing charge (USD)")
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="Percent")
    publisher = models.CharField(max_length=80, blank=True, db_index=True)
    official_website = models.URLField(max_length=300, blank=True)
    submission_portal_url = models.URLField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["acronym"]
        indexes = [
            models.Index(fields=["venue_type", "primary_domain"]),
            models.Index(fields=["country", "continent"]),
        ]

    def __str__(self):
        return self.acronym or self.name

    def get_absolute_url(self):
        return reverse("venues:detail", kwargs={"slug": self.slug})

    # ---- helpers -----------------------------------------------------
    @property
    def is_journal(self):
        return self.venue_type == self.VenueType.JOURNAL

    def _cycles(self):
        # Uses the prefetch cache when available.
        return list(self.cycles.all())

    @property
    def next_cycle(self):
        """The cycle whose next deadline is soonest; falls back to the latest past cycle."""
        now = timezone.now()
        cycles = self._cycles()
        upcoming = [c for c in cycles if c.next_deadline(now)]
        if upcoming:
            return min(upcoming, key=lambda c: c.next_deadline(now)[1])
        return max(cycles, key=lambda c: c.submission_deadline, default=None)

    @property
    def next_deadline(self):
        """(label, datetime) of the next upcoming deadline, else None."""
        cycle = self.next_cycle
        return cycle.next_deadline() if cycle else None

    @property
    def deadline_status(self):
        """One of 'rolling', 'open', 'upcoming', 'past' (matches the list filter)."""
        if self.is_rolling_submission:
            return "rolling"
        now = timezone.now()
        cycles = self._cycles()
        if any(c.is_open(now) for c in cycles):
            return "open"
        if any(c.open_date and c.open_date > now for c in cycles):
            return "upcoming"
        return "past"

    @property
    def rank_label(self):
        if self.is_journal:
            return self.quartile or "—"
        parts = []
        if self.core_rank != self.CoreRank.UNRANKED:
            parts.append(f"CORE {self.core_rank}")
        if self.ccf_rank != self.CcfRank.UNRANKED:
            parts.append(f"CCF {self.ccf_rank}")
        return " · ".join(parts) or "Unranked"

    @property
    def checklist(self):
        """Formatting checklist shown on the detail page."""
        items = [
            ("Template", f"Use {self.formatting_style}" if self.formatting_style else "See official call for papers"),
            ("Page limit", self.page_limit or "See call for papers"),
            ("Review model", self.review_process),
        ]
        if self.review_process == self.ReviewProcess.DOUBLE_BLIND:
            items.append(("Anonymity", "Remove author names, affiliations and self-identifying links"))
        items.append(("Open access", "Yes" + (f" (APC ${self.apc_cost_usd:,})" if self.apc_cost_usd else "") if self.is_open_access else "No (subscription / hybrid)"))
        if self.template_url:
            items.append(("Template link", self.template_url))
        return items

    # ---- copy-paste snippets ----------------------------------------
    @property
    def latex_snippet(self):
        style = (self.formatting_style or "").lower()
        if "acm" in style:
            doc = r"\documentclass[sigconf,review,anonymous]{acmart}" if "double" in self.review_process.lower() else r"\documentclass[sigconf]{acmart}"
        elif "ieee" in style:
            doc = r"\documentclass[conference]{IEEEtran}" if not self.is_journal else r"\documentclass[journal]{IEEEtran}"
        elif "lncs" in style or "springer" in style:
            doc = r"\documentclass[runningheads]{llncs}"
        elif "elsevier" in style:
            doc = r"\documentclass[review]{elsarticle}"
        elif "neurips" in style:
            doc = "\\documentclass{article}\n\\usepackage[preprint]{neurips_2025}"
        elif "nature" in style:
            doc = r"\documentclass[sn-nature]{sn-jnl}"
        else:
            doc = r"\documentclass[11pt]{article}"
        return (
            f"% {self.name} ({self.acronym})\n"
            f"% Formatting: {self.formatting_style or 'see call for papers'} | Limit: {self.page_limit or 'n/a'}\n"
            f"% Review: {self.review_process}\n"
            f"{doc}\n"
        )

    @property
    def bibtex(self):
        key = f"{slugify(self.acronym).replace('-', '')}{timezone.now().year}"
        kind = "article" if self.is_journal else "inproceedings"
        field = "journal" if self.is_journal else "booktitle"
        lines = [
            f"@{kind}{{{key},",
            "  author    = {Author, A. and Coauthor, B.},",
            "  title     = {Your Paper Title},",
            f"  {field} = {{{self.name}}},",
            f"  year      = {{{timezone.now().year}}},",
        ]
        if self.publisher:
            lines.append(f"  publisher = {{{self.publisher}}},")
        if self.issn:
            lines.append(f"  issn      = {{{self.issn}}},")
        lines.append("}")
        return "\n".join(lines)


class DeadlineCycle(models.Model):
    """One edition / submission cycle of a venue. All instants are stored in UTC."""

    class Tz(models.TextChoices):
        AOE = "AoE", "Anywhere on Earth (UTC-12)"
        UTC = "UTC", "UTC"

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="cycles")
    year = models.PositiveIntegerField(db_index=True)
    label = models.CharField(max_length=80, blank=True, help_text="e.g. 'NeurIPS 2027'")
    timezone_label = models.CharField(max_length=3, choices=Tz.choices, default=Tz.AOE)

    submission_open_date = models.DateTimeField(null=True, blank=True)
    abstract_deadline = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField(db_index=True)
    notification_date = models.DateTimeField(null=True, blank=True)
    camera_ready_date = models.DateTimeField(null=True, blank=True)
    event_start_date = models.DateField(null=True, blank=True)
    event_end_date = models.DateField(null=True, blank=True)
    is_projected = models.BooleanField(default=True, help_text="Dates extrapolated from previous editions; verify on the official site.")

    class Meta:
        ordering = ["-year"]
        constraints = [models.UniqueConstraint(fields=["venue", "year"], name="uniq_venue_cycle_year")]
        indexes = [models.Index(fields=["submission_deadline", "abstract_deadline"])]

    def __str__(self):
        return self.label or f"{self.venue.acronym} {self.year}"

    @property
    def open_date(self):
        return self.submission_open_date

    def is_open(self, now=None):
        now = now or timezone.now()
        start = self.submission_open_date
        return (start is None or start <= now) and now <= self.submission_deadline

    def milestones(self):
        """Ordered list of (key, label, datetime-or-date) tuples that are set."""
        rows = [
            ("abstract", "Abstract deadline", self.abstract_deadline),
            ("submission", "Paper submission deadline", self.submission_deadline),
            ("notification", "Author notification", self.notification_date),
            ("camera_ready", "Camera-ready", self.camera_ready_date),
            ("event_start", "Event starts", self.event_start_date),
            ("event_end", "Event ends", self.event_end_date),
        ]
        return [r for r in rows if r[2]]

    def next_deadline(self, now=None):
        """(label, datetime) of the abstract/paper deadline that is still ahead."""
        now = now or timezone.now()
        for label, value in (("Abstract", self.abstract_deadline), ("Paper", self.submission_deadline)):
            if value and value >= now:
                return label, value
        return None

    @property
    def submission_aoe(self):
        return self.submission_deadline + AOE_OFFSET


class VenueBookmark(models.Model):
    """Per-browser-session starred venues and personal notes (no login required)."""

    session_key = models.CharField(max_length=64, db_index=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="bookmarks")
    is_starred = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session_key", "venue"], name="uniq_bookmark_session_venue")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.venue.acronym} ({'★' if self.is_starred else 'note'})"
