"""Template filters for rendering Django form fields with Bootstrap classes."""
from django import template

register = template.Library()


@register.filter
def add_class(field, css_class):
    """Render a bound field's widget with *css_class* appended to its class attr.

    Widget attrs other than "class" are preserved (as_widget merges per key).
    """
    attrs = field.field.widget.attrs
    merged = f"{attrs.get('class', '')} {css_class}".strip()
    return field.as_widget(attrs={"class": merged})
