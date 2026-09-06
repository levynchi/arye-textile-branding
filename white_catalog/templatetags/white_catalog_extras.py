from django import template

from ..models import apply_price_list

register = template.Library()


@register.filter
def listed_price(price, user):
	"""Apply the customer's discount percent to a catalog unit/pack price."""
	return apply_price_list(price, user)
