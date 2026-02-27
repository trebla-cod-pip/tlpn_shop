from django import template

register = template.Library()


@register.filter(name='abs_val')
def abs_value(value):
    """Возвращает абсолютное значение числа"""
    try:
        return abs(float(value)) if value else 0
    except (ValueError, TypeError):
        return value or 0
