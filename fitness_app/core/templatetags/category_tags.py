from django import template

register = template.Library()

@register.filter
def split(value, arg=','):
    """
    Разделяет строку по разделителю
    Использование: {{ "тег1,тег2,тег3"|split:"," }}
    """
    if not value:
        return []
    return [item.strip() for item in value.split(arg) if item.strip()]

@register.filter
def trim(value):
    """
    Удаляет пробелы в начале и конце строки
    Использование: {{ "  текст  "|trim }}
    """
    if value:
        return value.strip()
    return value