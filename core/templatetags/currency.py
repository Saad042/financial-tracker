from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def pkr(value):
    """Format a number as PKR with comma separators."""
    try:
        value = Decimal(str(value))
    except Exception:
        return value
    sign = "-" if value < 0 else ""
    value = abs(value)
    formatted = f"{value:,.2f}"
    return f"{sign}PKR {formatted}"
