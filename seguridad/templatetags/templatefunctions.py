from django import template
from django.core import signing

register = template.Library()


@register.filter
def get_decrypt(cyphertxt):
    try:
        return signing.loads(cyphertxt)
    except Exception as ex:
        return ""


@register.filter('startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.lower().startswith(starts.lower())
    return False


@register.simple_tag
def traducir_permiso(value):
    valor = str(value).lower()
    es_permiso_de_django = 'can add' in valor or 'can view' in valor or 'can change' in valor or 'can delete' in valor
    if es_permiso_de_django:
        return ' '.join(valor.replace("can", "Puede") \
                        .replace('add', 'Agregar') \
                        .replace('view', 'Ver') \
                        .replace('delete', 'Eliminar') \
                        .replace('change', 'Modificar').split(' ')[0:2])
    return value


@register.filter
def abreviar(value):
    """Contadores del panel: 12.400 -> '12,4 k', 49.603.804 -> '49,6 M'.
    Bajo 10.000 se muestra el número tal cual (con miles) para no perder precisión visual."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value
    signo = '-' if n < 0 else ''
    n = abs(n)
    if n >= 1_000_000:
        txt, suf = n / 1_000_000, ' M'
    elif n >= 10_000:
        txt, suf = n / 1_000, ' k'
    else:
        entero = int(n)
        if n == entero:
            return f'{signo}{entero:,}'.replace(',', '.')
        return f'{signo}{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    txt = f'{txt:.1f}'.rstrip('0').rstrip('.')
    return f"{signo}{txt.replace('.', ',')}{suf}"

