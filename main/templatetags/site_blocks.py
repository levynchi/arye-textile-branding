from django import template
from ..models import Banner

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
