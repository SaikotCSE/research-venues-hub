"""Invalidate catalogue-derived caches (facets, insights) whenever venue data changes."""
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import DeadlineCycle, ResearchSubfield, Venue, bump_catalog_version


@receiver(post_save, sender=Venue)
@receiver(post_delete, sender=Venue)
@receiver(post_save, sender=DeadlineCycle)
@receiver(post_delete, sender=DeadlineCycle)
@receiver(post_save, sender=ResearchSubfield)
@receiver(post_delete, sender=ResearchSubfield)
@receiver(m2m_changed, sender=Venue.subfields.through)
def catalog_changed(sender, **kwargs):
    bump_catalog_version()
