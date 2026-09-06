from decimal import Decimal

from django import template

from ..models import apply_price_list

register = template.Library()


@register.filter
def listed_price(price, user):
	"""Apply the customer's discount percent to a catalog unit/pack price."""
	return apply_price_list(price, user)


@register.filter
def has_price_discount(user):
	"""True when the customer has a discount greater than zero."""
	if user is None:
		return False
	percent = getattr(user, "price_percent", None)
	if percent is None:
		return False
	if not isinstance(percent, Decimal):
		percent = Decimal(str(percent))
	return percent > 0
