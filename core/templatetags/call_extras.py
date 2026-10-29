from django import template

register = template.Library()


@register.filter
def call(obj, arg):
    """Call a stored callable with the row argument, or return obj as-is."""
    if callable(obj):
        try:
            result = obj(arg)
            return "" if result is None else result
        except Exception:
            return ""
    return obj


@register.filter
def get_field_label(form, field_name):
    """
    Return the human-readable label of a form field.

    Usage:
        {{ form|get_field_label:field_name }}
    """
    if field_name == "__all__":
        return "General"
    try:
        field = form.fields.get(field_name)
        if field is not None:
            return field.label or field_name.replace("_", " ").title()
    except (AttributeError, TypeError):
        pass
    return field_name.replace("_", " ").title()


@register.filter
def split_csv(value):
    """
    Split a comma-separated string into a list of trimmed non-empty items.

    Usage:
        {% for amount in "10,20,30"|split_csv %}
    """
    if value in (None, ""):
        return []
    return [s.strip() for s in str(value).split(",") if s.strip()]


@register.filter
def split_pairs(value, sep=","):
    """
    Split 'a:1,b:2' into [('a', '1'), ('b', '2')].

    Usage:
        {% for key, label in "identity:Identity,contact:Contact"|split_pairs %}
    """
    if value in (None, ""):
        return []
    pairs = []
    for item in str(value).split(sep):
        if ":" in item:
            k, v = item.split(":", 1)
            pairs.append((k.strip(), v.strip()))
    return pairs


@register.filter
def dict_get(d, key):
    """
    Safe dict lookup that returns None instead of raising on missing keys.

    Usage:
        {{ form|dict_get:field_name }}
    """
    try:
        return d[key]
    except (KeyError, TypeError, IndexError):
        return None

# reports/templatetags/form_extras.py
from django import template
register = template.Library()

@register.filter
def get_field(form, name):
    return form[name] if name in form.fields else None