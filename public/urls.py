from django.urls import path, re_path

from .view_changepass import changepass
from .view_landing import landing
from .view_restaurar import restaurar
from .view_login import login_tienda, logout_tienda
from .view_portal import agendar, cita_cliente, conectar, incrustar
from .view_recordarusername import recordarusername
from .view_terminoscondiciones import proteccion_datos, terminosycondiciones

urlpatterns = [
    path('', landing),
    re_path(r'^login/', login_tienda),
    re_path(r'^logout/', logout_tienda),
    re_path(r'^restorepass/', restaurar),
    re_path(r'^restoreusername/', recordarusername),
    re_path(r'^changepass/', changepass),
    path('privacidad/', terminosycondiciones),
    path('terminosycondiciones/', terminosycondiciones),
    path('proteccion-datos/', proteccion_datos),
    path('agendar/<slug:slug>/', agendar),
    path('cita/<str:token>/', cita_cliente),
    path('conectar/<slug:portal>/<str:token>/', conectar),
    path('incrustar/<slug:portal>/', incrustar),
]
