"""Búsqueda global de la agenda: clientes, citas y solicitudes en una sola consulta.

`buscar(texto, usuario, limite=8)` devuelve un dict con listas `clientes`, `citas`, `solicitudes`. Usa
`unaccent` + `icontains` (migración 0008 instala `unaccent` y `pg_trgm`); si el texto parece un código
(QW-…, CL-…, REQ-…) prioriza la coincidencia exacta. El alcance respeta los permisos: quien no es líder
general ni coordinador ve solo las citas en las que participa y las solicitudes de sus equipos.
"""
from django.db.models import Q

from .funciones_permisos import equipos_visibles, es_coordinador, es_lider_general
from .models import Cita, Cliente, Solicitud


def _normalizar(texto):
    return ' '.join((texto or '').split())[:120]


def buscar(texto, usuario, limite=8):
    texto = _normalizar(texto)
    vacio = {'texto': texto, 'clientes': [], 'citas': [], 'solicitudes': [], 'total': 0}
    if len(texto) < 2:
        return vacio
    todo = es_lider_general(usuario) or es_coordinador(usuario)
    q_cliente = (Q(nombres__unaccent__icontains=texto) | Q(correo__icontains=texto) | Q(telefono__icontains=texto)
                 | Q(codigo__iexact=texto))
    clientes = list(Cliente.objects.filter(status=True).filter(q_cliente).order_by('nombres')[:limite])
    citas = Cita.objects.filter(status=True).select_related('cliente', 'producto', 'equipo')
    if not todo:
        citas = citas.filter(participantes__usuario=usuario, participantes__status=True).distinct()
    q_cita = (Q(codigo__iexact=texto) | Q(titulo__unaccent__icontains=texto) | Q(cliente__nombres__unaccent__icontains=texto)
              | Q(cliente__correo__icontains=texto))
    citas = list(citas.filter(q_cita).order_by('-inicio')[:limite])
    solicitudes = Solicitud.objects.filter(status=True).select_related('cliente', 'producto', 'equipo')
    if not todo:
        solicitudes = solicitudes.filter(Q(equipo__in=equipos_visibles(usuario)) | Q(equipo__isnull=True))
    q_sol = (Q(codigo__iexact=texto) | Q(cliente__nombres__unaccent__icontains=texto) | Q(motivo__unaccent__icontains=texto)
             | Q(cliente__correo__icontains=texto))
    solicitudes = list(solicitudes.filter(q_sol).order_by('-fecha_registro')[:limite])
    return {'texto': texto, 'clientes': clientes, 'citas': citas, 'solicitudes': solicitudes,
            'total': len(clientes) + len(citas) + len(solicitudes)}
