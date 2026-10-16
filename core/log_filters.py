import logging
import re

# Familia de credenciales que suelen viajar en URLs, pensada
# para el TEXTO de un log (además de & corta en comillas y espacios): tapa el valor de
# wstoken/token/password/apikey/key= venga de donde venga.
_RE_CRED = re.compile(r'((?:wstoken|token|password|apikey|api_key|key)=)[^&\s"\']+', re.IGNORECASE)

# El token que viaja en la cabecera, no en la URL: el plugin autentica con `Authorization: Bearer`
# y cualquier volcado de la petición lo deja escrito.
_RE_BEARER = re.compile(r'(Bearer\s+)[A-Za-z0-9._\-]{8,}', re.IGNORECASE)

# Datos personales: las cédulas y correos no tienen
# por qué quedar en un archivo de log que se rota, se copia y se mira desde varias manos.
_RE_CORREO = re.compile(r'\b([\w.+-])[\w.+-]*(@[\w-]+\.[\w.]+)\b')
_RE_CEDULA = re.compile(r'\b((?:c[eé]dula|documento|dni|identificaci[oó]n)\W{0,4})(\d{6,13})\b',
                        re.IGNORECASE)


class ScrubCredentialsFilter(logging.Filter):
    """Tapa credenciales y datos personales en cualquier registro antes de escribirlo.

    Defensa en profundidad: una excepción de red de `requests` reconstruye la URL final con el
    token en el mensaje, y basta un `logger.warning('%s', exc)` para dejarlo en claro en el
    archivo. Este filtro cubre todos esos sitios de una sola vez, incluidos los que se agreguen
    después. No filtra nada (siempre devuelve True); solo reescribe el mensaje si hace falta.
    """

    def filter(self, record):
        try:
            mensaje = record.getMessage()
        except Exception:
            return True
        limpio = mensaje
        bajo = mensaje.lower()
        if 'token=' in bajo or 'key=' in bajo or 'password=' in bajo:
            limpio = _RE_CRED.sub(r'\1***', limpio)
        if 'bearer' in bajo:
            limpio = _RE_BEARER.sub(r'\1***', limpio)
        if '@' in limpio:
            # Queda la inicial y el dominio: alcanza para seguir un caso sin exponer a la persona.
            limpio = _RE_CORREO.sub(r'\1***\2', limpio)
        if any(p in bajo for p in ('cedula', 'cédula', 'documento', 'dni', 'identificacion',
                                   'identificación')):
            limpio = _RE_CEDULA.sub(lambda m: f'{m.group(1)}{m.group(2)[:2]}******', limpio)
        if limpio != mensaje:
            record.msg = limpio
            record.args = ()
        return True
