"""
Template filters para la app de queries
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Obtiene un valor de un diccionario usando una clave.
    Uso: {{ params_used|get_item:param.posicion_where }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
