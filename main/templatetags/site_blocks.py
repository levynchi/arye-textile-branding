from django import template
from ..models import Banner
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.inclusion_tag("partials/hero.html", takes_context=True)
def hero(context, page: str | None = None):
    """Render the hero/banner for a page.

    If page is None, try to infer from request's url_name; fall back to 'home'.
    """
    request = context.get("request")
    slug = page
    if not slug and request is not None:
        match = getattr(request, "resolver_match", None)
        if match and match.url_name:
            slug = match.url_name
    if not slug:
        slug = "home"
    return {"banner": Banner.for_page(slug)}


@register.filter(name="resolve_link")
def resolve_link(value: str | None):
    """Resolve a string into a navigable URL.

    Rules:
    - If empty -> '#'
    - If starts with 'http', 'https', '/', or '#' -> return as-is
    - Otherwise treat as URL name for reverse(); if fails, return '/<value>/' style path
    """
    s = (value or "").strip()
    if not s:
        return "#"
    lower = s.lower()
    if lower.startswith("http://") or lower.startswith("https://") or s.startswith("/") or s.startswith("#"):
        return s
    try:
        return reverse(s)
    except NoReverseMatch:
        return "/" + s.strip("/") + "/"
