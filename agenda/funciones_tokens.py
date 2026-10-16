"""Enlaces sin contraseña para el cliente (`TokenAcceso`).

- `emitir(tipo, cita=None, cliente=None, request=None)` → token en claro (solo se guarda su hash).
- `validar(token, tipo)` → `TokenAcceso` vigente o `None`; registra el uso y renueva el enlace personal.
- `url_cita(token)` / `url_cliente(portal, token)` → URL absoluta para el correo.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings

from seguridad.models import ParametroSistema
from .models import TokenAcceso

VIGENCIA_CITA_DIAS = 60


def _hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _meses_enlace_personal():
    try:
        return int(ParametroSistema.valor_de('cliente_vigencia_enlace_meses', 12))
    except (TypeError, ValueError):
        return 12


def emitir(tipo, cita=None, cliente=None, request=None):
    token = secrets.token_urlsafe(32)
    if tipo == 'cita':
        vence = max(cita.fin, datetime.now()) + timedelta(days=VIGENCIA_CITA_DIAS)
    else:
        vence = datetime.now() + timedelta(days=30 * _meses_enlace_personal())
    TokenAcceso(tipo=tipo, token_hash=_hash(token), cita=cita, cliente=cliente, vence=vence).save(request)
    return token


def validar(token, tipo):
    if not token or len(token) > 120:
        return None
    acceso = (TokenAcceso.objects.filter(status=True, tipo=tipo, token_hash=_hash(token), revocado=False)
              .select_related('cita', 'cliente').first())
    if acceso is None or acceso.vence < datetime.now():
        return None
    acceso.usos += 1
    acceso.ultimo_uso = datetime.now()
    if tipo == 'cliente':
        acceso.vence = datetime.now() + timedelta(days=30 * _meses_enlace_personal())
    acceso.save(update_fields=['usos', 'ultimo_uso', 'vence'])
    return acceso


def revocar_de_cita(cita, request=None):
    for t in TokenAcceso.objects.filter(status=True, cita=cita, revocado=False):
        t.revocado = True
        t.save(request)


def base_publica():
    return (getattr(settings, 'BACKEND_PUBLIC_URL', '') or '').rstrip('/')


def url_cita(token):
    return f'{base_publica()}/cita/{token}/'


def url_cliente(portal, token):
    slug = portal.slug if portal is not None else 'turno'
    return f'{base_publica()}/conectar/{slug}/{token}/'
