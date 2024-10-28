# myapp/templatetags/custom_filters.py

from django import template
import json

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter
def to_json(value):
    return json.dumps(value)


@register.filter
def trim_after_self_serve(value):
    if "self-serve" in value:
        return value.split("self-serve")[0] + "self-serve"
    return value