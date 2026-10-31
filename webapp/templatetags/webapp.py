import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from webapp import vite

register = template.Library()


@register.simple_tag(takes_context=True)
def vite_assets(context, page_module=None):
    """<link>/<script> tags for the app bundle (or the Vite dev server when VITE_DEV_SERVER_URL is set)."""
    nonce = context.get("csp_nonce", "")
    dev = vite.dev_server()
    if dev:
        preamble = (
            f'import RefreshRuntime from "{dev}/@react-refresh";'
            "RefreshRuntime.injectIntoGlobalHook(window);"
            "window.$RefreshReg$ = () => {};"
            "window.$RefreshSig$ = () => (type) => type;"
            "window.__vite_plugin_react_preamble_installed__ = true;"
        )
        return format_html(
            '<script type="module" nonce="{}">{}</script>\n<script type="module" src="{}/@vite/client"></script>\n'
            '<script type="module" src="{}/{}"></script>',
            nonce,
            mark_safe(preamble),  # noqa: S308 - constant string built from settings
            dev,
            dev,
            vite.ENTRY,
        )
    assets = vite.entry_assets(page_module=page_module)
    parts = [
        format_html_join("\n", '<link rel="preload" href="{}" as="font" type="font/woff2" crossorigin>', ((f,) for f in assets["fonts"])),
        format_html_join("\n", '<link rel="stylesheet" href="{}">', ((s,) for s in assets["styles"])),
        format_html_join("\n", '<link rel="modulepreload" href="{}">', ((p,) for p in assets["preloads"])),
        format_html('<script type="module" src="{}"></script>', assets["script"]),
    ]
    return mark_safe("\n".join(p for p in parts if p))  # noqa: S308 - every part is escaped by format_html


@register.simple_tag
def jsonld(data):
    """A schema.org JSON-LD block, escaped like Django's json_script."""
    payload = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False)
    payload = payload.replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026")
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')  # noqa: S308 - escaped above
