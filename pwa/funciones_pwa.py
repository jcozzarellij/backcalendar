import hashlib
import io
import math
import os
from functools import lru_cache

from django.conf import settings
from PIL import Image, ImageOps

TAMANOS_ICONO = (72, 96, 128, 144, 152, 180, 192, 384, 512)
TAMANOS_MANIFEST = (72, 96, 128, 144, 152, 192, 384, 512)
TAMANOS_MASKABLE = (192, 512)

ZONA_NORMAL = 0.84
ZONA_MASKABLE = 0.76
FONDO_ICONO = '#ffffff'

ICONO_BASE = os.path.join(settings.BASE_DIR, 'static', 'images', 'icons', 'icon-512x512.png')
CARPETA_ICONOS = os.path.join(settings.MEDIA_ROOT, 'pwa', 'iconos')
CARPETA_CAPTURAS = os.path.join(settings.BASE_DIR, 'static', 'images', 'pwa', 'capturas')
URL_CAPTURAS = '/static/images/pwa/capturas/'


def armar_icono(origen, tamano, maskable=False):
    """Centra la imagen sobre un lienzo cuadrado de `tamano` px.

    El ícono normal ocupa hasta el 84% del lado. El maskable se escala por la diagonal
    para que entre completo en el círculo seguro del 80% que recortan Android y Chrome."""
    with Image.open(origen) as original:
        imagen = ImageOps.exif_transpose(original).convert('RGBA')
    recorte = imagen.getbbox()
    if recorte:
        imagen = imagen.crop(recorte)
    ancho, alto = imagen.size
    if maskable:
        escala = tamano * ZONA_MASKABLE / math.hypot(ancho, alto)
    else:
        escala = tamano * ZONA_NORMAL / max(ancho, alto)
    medida = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    imagen = imagen.resize(medida, Image.LANCZOS)
    lienzo = Image.new('RGBA', (tamano, tamano), FONDO_ICONO)
    lienzo.alpha_composite(imagen, ((tamano - medida[0]) // 2, (tamano - medida[1]) // 2))
    salida = io.BytesIO()
    lienzo.convert('RGB').save(salida, format='PNG', optimize=True)
    return salida.getvalue()


def version_icono(confi):
    logo = confi.logo_sistema.name if confi and confi.logo_sistema else 'base'
    firma = f'{logo}|{ZONA_NORMAL}|{ZONA_MASKABLE}|{FONDO_ICONO}'
    return hashlib.md5(firma.encode('utf-8')).hexdigest()[:10]


def obtener_icono(confi, tamano, maskable=False):
    """Ícono cuadrado de la PWA armado desde el logo del sistema, cacheado en disco.

    El nombre del archivo lleva la versión del logo: al subir otro logo cambia la versión,
    se genera de nuevo y se borran los íconos de la versión anterior. Sin logo, o si el
    logo no se puede leer, se usa el ícono base de `static/images/icons/`."""
    version = version_icono(confi)
    ruta = os.path.join(CARPETA_ICONOS, f"{version}-{tamano}{'-maskable' if maskable else ''}.png")
    if os.path.exists(ruta):
        with open(ruta, 'rb') as archivo:
            return archivo.read()

    contenido = None
    if confi and confi.logo_sistema:
        try:
            with confi.logo_sistema.storage.open(confi.logo_sistema.name, 'rb') as archivo:
                contenido = armar_icono(archivo, tamano, maskable)
        except Exception:
            contenido = None
    if contenido is None:
        contenido = armar_icono(ICONO_BASE, tamano, maskable)

    try:
        os.makedirs(CARPETA_ICONOS, exist_ok=True)
        for anterior in os.listdir(CARPETA_ICONOS):
            if not anterior.startswith(f'{version}-'):
                os.remove(os.path.join(CARPETA_ICONOS, anterior))
        with open(ruta, 'wb') as archivo:
            archivo.write(contenido)
    except OSError:
        pass
    return contenido


@lru_cache(maxsize=32)
def _medida_imagen(ruta, modificado):
    with Image.open(ruta) as imagen:
        return imagen.size


def capturas_manifest():
    """Capturas de `PWA_APP_SCREENSHOTS` que existen en disco, con su medida real.

    Chrome descarta la lista si una medida declarada no coincide con la imagen, si un lado
    queda fuera de 320-3840 px o si la proporción supera 2.3:1; por eso se mide cada archivo
    y se omite el que no cumple. `wide` debe ser apaisada y `narrow` vertical."""
    capturas = []
    for item in getattr(settings, 'PWA_APP_SCREENSHOTS', []):
        ruta = os.path.join(CARPETA_CAPTURAS, item['archivo'])
        try:
            modificado = os.path.getmtime(ruta)
            ancho, alto = _medida_imagen(ruta, modificado)
        except Exception:
            continue
        if min(ancho, alto) < 320 or max(ancho, alto) > 3840 or max(ancho, alto) / min(ancho, alto) > 2.3:
            continue
        if (item['form_factor'] == 'wide') != (ancho > alto):
            continue
        capturas.append({
            'src': f"{URL_CAPTURAS}{item['archivo']}?v={int(modificado)}",
            'sizes': f'{ancho}x{alto}',
            'type': 'image/png',
            'form_factor': item['form_factor'],
            'label': item['label'],
        })
    return capturas
