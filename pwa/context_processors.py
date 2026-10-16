from django.conf import settings


def pwa_settings(request):
    webpush = getattr(settings, 'WEBPUSH_SETTINGS', {}) or {}
    try:
        from seguridad.models import Configuracion
        from .funciones_pwa import version_icono
        icono_version = version_icono(Configuracion.get_instancia())
    except Exception:
        icono_version = ''
    return {
        'pwa_install_cooldown_hours': getattr(settings, 'PWA_INSTALL_COOLDOWN_HOURS', 10),
        'pwa_icono_version': icono_version,
        'vapid_key': webpush.get('VAPID_PUBLIC_KEY', ''),
    }
