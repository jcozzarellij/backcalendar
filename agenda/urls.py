from django.urls import re_path

from .view_agenda import agendaView
from .view_agenda_equipo import agendaEquipoView
from .view_alertas import alertasView
from .view_buscar import buscarView
from .view_aplicaciones import aplicacionesView
from .view_cita import citaView
from .view_cliente import clienteView
from .view_cola import colaView
from .view_equipo import equipoView
from .view_feriado import feriadoView
from .view_mi_dia import miDiaView
from .view_parametros import parametrosAgendaView
from .view_portal import portalView
from .view_proyecto import proyectoView
from .view_solicitud import solicitudView
from .view_turnos import turnosView

agenda_urls = (
    {
        "nombre": "Hoy",
        "url": 'mi-dia/',
        "vista": miDiaView,
    },
    {
        "nombre": "Calendario",
        "url": 'mi-agenda/',
        "vista": agendaView,
    },
    {
        "nombre": "Citas",
        "url": 'citas/',
        "vista": citaView,
    },
    {
        "nombre": "Buscar",
        "url": 'buscar/',
        "vista": buscarView,
    },
    {
        "nombre": "Alertas",
        "url": 'alertas/',
        "vista": alertasView,
    },
    {
        "nombre": "Conexiones",
        "url": 'aplicaciones/',
        "vista": aplicacionesView,
    },
    {
        "nombre": "Horarios",
        "url": 'mis-turnos/',
        "vista": turnosView,
    },
    {
        "nombre": "Agenda del equipo",
        "url": 'agenda-equipo/',
        "vista": agendaEquipoView,
    },
    {
        "nombre": "Horarios del equipo",
        "url": 'turnos-equipo/',
        "vista": turnosView,
    },
    {
        "nombre": "Proyectos",
        "url": 'proyectos/',
        "vista": proyectoView,
    },
    {
        "nombre": "Equipos",
        "url": 'equipos/',
        "vista": equipoView,
    },
    {
        "nombre": "Feriados",
        "url": 'feriados/',
        "vista": feriadoView,
    },
    {
        "nombre": "Cola de solicitudes",
        "url": 'cola/',
        "vista": colaView,
    },
    {
        "nombre": "Solicitudes",
        "url": 'solicitudes/',
        "vista": solicitudView,
    },
    {
        "nombre": "Clientes",
        "url": 'clientes/',
        "vista": clienteView,
    },
    {
        "nombre": "Portales y productos",
        "url": 'portales/',
        "vista": portalView,
    },
    {
        "nombre": "Parámetros",
        "url": 'parametros/',
        "vista": parametrosAgendaView,
    },
)

urlpatterns = [
    re_path(r'^aplicaciones/google/$', aplicacionesView),
    re_path(r'^citas/(?P<pk>\d+)/$', citaView),
    re_path(r'^clientes/(?P<pk>\d+)/$', clienteView),
]

for u in agenda_urls:
    urlpatterns.append(re_path(r'^{}$'.format(u["url"]), u["vista"]))
