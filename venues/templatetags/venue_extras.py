from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.filter
def has_param(params, spec):
    """{% if request.GET|has_param:'core:A*' %} -> True when that value is selected."""
    key, _, value = spec.partition(":")
    try:
        return value in params.getlist(key)
    except AttributeError:
        return False


@register.filter
def iso(dt):
    return dt.isoformat() if dt else ""


@register.filter
def rank_class(venue):
    best = venue.core_rank if venue.core_rank != "Unranked" else venue.quartile
    return {
        "A*": "bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-300",
        "Q1": "bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-300",
        "A": "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300",
        "Q2": "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300",
        "B": "bg-sky-100 text-sky-800 dark:bg-sky-400/15 dark:text-sky-300",
        "Q3": "bg-sky-100 text-sky-800 dark:bg-sky-400/15 dark:text-sky-300",
    }.get(best, "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300")


@register.filter
def status_class(status):
    return {
        "open": "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300",
        "upcoming": "bg-sky-100 text-sky-800 dark:bg-sky-400/15 dark:text-sky-300",
        "rolling": "bg-violet-100 text-violet-800 dark:bg-violet-400/15 dark:text-violet-300",
        "past": "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    }.get(status, "")


@register.simple_tag
def checked(params, key, value):
    """Emit the ``checked`` attribute when ``value`` is among the selected values of ``key``."""
    try:
        return "checked" if str(value) in params.getlist(key) else ""
    except AttributeError:
        return ""


@register.simple_tag
def icon(name, css="h-4 w-4", label=""):
    """Render a Lucide icon from the local sprite: {% icon "search" "h-4 w-4" %}.

    Icons are decorative (aria-hidden) unless ``label`` is given, in which case they get role="img".
    """
    href = f"{static('venues/img/icons.svg')}#{name}"
    if label:
        return format_html(
            '<svg class="icon {}" role="img" aria-label="{}" focusable="false" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><use href="{}"></use></svg>',
            css, label, href,
        )
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><use href="{}"></use></svg>',
        css, href,
    )
