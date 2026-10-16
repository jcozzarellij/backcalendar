import json

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from .funciones_pwa import (
    TAMANOS_ICONO, TAMANOS_MANIFEST, TAMANOS_MASKABLE, capturas_manifest, obtener_icono, version_icono,
)


def _get_configuracion():
    try:
        from seguridad.models import Configuracion
        return Configuracion.get_instancia()
    except Exception:
        return None


def _build_icons(confi):
    version = version_icono(confi)
    iconos = [
        {'src': f'/pwa/icono/{t}.png?v={version}', 'sizes': f'{t}x{t}', 'type': 'image/png', 'purpose': 'any'}
        for t in TAMANOS_MANIFEST
    ]
    iconos += [
        {'src': f'/pwa/icono/{t}-maskable.png?v={version}', 'sizes': f'{t}x{t}', 'type': 'image/png', 'purpose': 'maskable'}
        for t in TAMANOS_MASKABLE
    ]
    return iconos


@cache_control(max_age=86400, public=True)
def icono(request, tamano, maskable=False):
    if tamano not in TAMANOS_ICONO:
        raise Http404('Tamaño de ícono no disponible.')
    return HttpResponse(obtener_icono(_get_configuracion(), tamano, maskable), content_type='image/png')


@cache_control(max_age=300, public=True)
def manifest(request):
    confi = _get_configuracion()
    nombre = (confi.nombre_empresa if confi else None) or getattr(settings, 'PWA_APP_NAME', 'Turno')
    short = ((confi.alias if confi else None) or getattr(settings, 'PWA_APP_SHORT_NAME', nombre))[:12] or 'app'
    descripcion = (confi.descripcion if confi else None) or getattr(settings, 'PWA_APP_DESCRIPTION', '')

    payload = {
        'name': nombre,
        'short_name': short,
        'description': descripcion,
        'start_url': getattr(settings, 'PWA_APP_START_URL', '/panel/'),
        'display': getattr(settings, 'PWA_APP_DISPLAY', 'standalone'),
        'scope': getattr(settings, 'PWA_APP_SCOPE', '/'),
        'orientation': getattr(settings, 'PWA_APP_ORIENTATION', 'any'),
        'background_color': getattr(settings, 'PWA_APP_BACKGROUND_COLOR', '#ffffff'),
        'theme_color': getattr(settings, 'PWA_APP_THEME_COLOR', '#2874A6'),
        'lang': getattr(settings, 'PWA_APP_LANG', 'es-ES'),
        'dir': getattr(settings, 'PWA_APP_DIR', 'auto'),
        'icons': _build_icons(confi),
    }
    capturas = capturas_manifest()
    if capturas:
        payload['screenshots'] = capturas
    return JsonResponse(payload)


def service_worker(request):
    response = render(request, 'pwa/service_worker.js')
    response['Content-Type'] = 'application/javascript'
    return response


def offline(request):
    return render(request, 'pwa/offline.html')


@require_POST
def push_subscription_status(request):
    if not getattr(request.user, 'is_authenticated', False):
        return JsonResponse({'registered': False, 'authenticated': False})
    endpoint = ''
    try:
        body = json.loads((request.body or b'').decode('utf-8') or '{}')
        endpoint = (body.get('endpoint') or '').strip()
    except Exception:
        endpoint = ''
    if not endpoint:
        return JsonResponse({'registered': False})
    try:
        from webpush.models import PushInformation
        registered = PushInformation.objects.filter(
            user=request.user,
            subscription__endpoint=endpoint,
        ).exists()
    except Exception:
        registered = True
    return JsonResponse({'registered': registered})
