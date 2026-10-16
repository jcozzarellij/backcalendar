from django.urls import re_path

from public.view_login import login_tienda
from .view_login import logout_user
from .adm_usuario import administradorView

autenticacion_urls = (
    {
        "nombre": "Administrativos",
        "url": 'usuario/',
        "vista": administradorView,
    },
)

urlpatterns = [
    re_path(r'^login/', login_tienda, name='login_url'),
    re_path(r'^logout/', logout_user, name='logout_url'),
]

for u in autenticacion_urls:
    urlpatterns.append(re_path(r'^{}$'.format(u["url"]), u["vista"]))