"""Sirve únicamente recursos de presentación y distribuciones públicas en desarrollo."""
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.http import Http404
from django.views.static import serve

PUBLICOS = ('configuracion/', 'fotousuario/', 'pwa/', 'productos/')
EXTENSIONES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.tiff', '.jfif'}
PREDEFINIDOS = {'foto_defaultd.png', 'loadmail.gif', 'no-image.webp'}


def media_publica(request, path):
    relativa = PurePosixPath(path)
    if (relativa.is_absolute() or '..' in relativa.parts or '\\' in path
            or not (path in PREDEFINIDOS or
                    (path.startswith(PUBLICOS) and relativa.suffix.lower() in EXTENSIONES))):
        raise Http404
    raiz = Path(settings.MEDIA_ROOT).resolve()
    archivo = raiz.joinpath(*relativa.parts)
    if any(p.is_symlink() for p in [archivo, *archivo.parents] if p != raiz and raiz in p.parents):
        raise Http404
    if not archivo.resolve().is_relative_to(raiz):
        raise Http404
    return serve(request, path, document_root=str(raiz))
