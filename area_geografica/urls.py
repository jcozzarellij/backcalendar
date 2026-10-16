from django.urls import re_path

from .view_ciudad import ciudadView
from .view_pais import paisView
from .view_provincia import provinciaView

area_geografica_urls = (
    {
        "nombre": "País",
        "url": 'pais/',
        "vista": paisView,
    },
    {
        "nombre": "Provincia",
        "url": 'provincia/',
        "vista": provinciaView,
    },
    {
        "nombre": "Ciudad",
        "url": 'ciudad/',
        "vista": ciudadView,
    },
)

urlpatterns = [

]

for u in area_geografica_urls:
    urlpatterns.append(re_path(r'^{}$'.format(u["url"]), u["vista"]))
