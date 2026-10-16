from django.contrib import admin
from django.urls import path, include, re_path

from agenda.urls import agenda_urls
from area_geografica.urls import area_geografica_urls
from django.views.generic import RedirectView

from autenticacion.urls import autenticacion_urls
from autenticacion.view_perfil import perfilView
from core.ajax import ConsultasAjax
from backcalendar.view_clearsitedata import clearSiteDataView
from backcalendar.view_health import health_view
from backcalendar import settings
from backcalendar.view_redirect import redirectToUrlView
from seguridad.models import Configuracion
from seguridad.urls import seguridad_urls
from seguridad.view_index import index
from core.media_publica import media_publica
from core.consultas import consultas
from seguridad.view_notificaciones import notificacionesView

confi = Configuracion.get_instancia()
icon_url = confi.ico.url if confi.ico else ""
favicon_view = RedirectView.as_view(url=icon_url, permanent=True)
urls_sistema = (
    {
        "nombre": "Agenda",
        "url": 'agenda/',
        "sub_urls": agenda_urls,
        "include": include('agenda.urls'),
        "name": None,
        "vista": None
    },
    {
        "nombre": "Áreas Geográficas",
        "url": "area-geografica/",
        "sub_urls": area_geografica_urls,
        "include": include('area_geografica.urls'),
        "name": None,
        "vista": None
    },
    {
        "nombre": "Autenticación",
        "url": 'autenticacion/',
        "sub_urls": autenticacion_urls,
        "include": include('autenticacion.urls'),
        "name": None,
        "vista": None
    },
    {
        "nombre": "Seguridad",
        "url": 'seguridad/',
        "sub_urls": seguridad_urls,
        "include": include('seguridad.urls'),
        "name": None,
        "vista": None
    },
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_view, name='health_check'),
    path('panel/', index),
    path('notificaciones/', notificacionesView),
    path('perfilpanel/', perfilView),
    path('consultas/', consultas, name='Consultas API'),
    path('ajaxrequest/<slug:accion>', ConsultasAjax.as_view(), name='Ajax Consultas v1'),
    path('redirect-to-url/<int:pk>/', redirectToUrlView),
    re_path(r'^favicon\.ico', favicon_view),
    path('clear-site-data/', clearSiteDataView),
    path("select2/", include("django_select2.urls")),
    path('', include('public.urls')),
    path('webpush/', include('webpush.urls')),
    path('', include('pwa.urls')),
]

if settings.DEBUG:
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', media_publica)]

for u in urls_sistema:
    if u["vista"] and not u["include"]:
        if u["name"]:
            urlpatterns.append(path('{}'.format(u["url"]), u["vista"], name=u["name"]))
        else:
            urlpatterns.append(path('{}'.format(u["url"]), u["vista"]))
    elif not u["vista"] and u["include"]:
        if u["name"]:
            urlpatterns.append(path('{}'.format(u["url"]), u["include"], name=u["name"]))
        else:
            urlpatterns.append(path('{}'.format(u["url"]), u["include"]))


admin.site.site_header = "{} {}".format("Administración", "backcalendar")
admin.site.site_title = "{} {}".format("Administración", "backcalendar")
