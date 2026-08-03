from django import template
from apps.core.submodules import MODULE_LABELS

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """Template-side dict.get(key) — Django's dot-lookup can't take a variable key."""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def module_label(module_code):
    """e.g. 'lab' -> 'Laboratory'"""
    return MODULE_LABELS.get(module_code, module_code.replace('_', ' ').title())
