from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from area_geografica.models import Pais, Provincia
from core.funciones import rate_limit


@login_required
@rate_limit(limit=60, seconds=60)
def consultas(request):
    if request.method == 'GET' and 'action' in request.GET:
        action = request.GET['action']
        try:
            if action == 'provincias':
                pais = Pais.objects.get(pk=request.GET['id'])
                lista = [[p.id, p.nombre] for p in pais.provincia_set.filter(status=True).order_by('nombre')]
                return JsonResponse({'result': 'ok', 'lista': lista})
            if action == 'cantones':
                provincia = Provincia.objects.get(pk=request.GET['id'])
                lista = [[c.id, c.nombre] for c in provincia.ciudad_set.filter(status=True).order_by('nombre')]
                return JsonResponse({'result': 'ok', 'lista': lista})
        except Exception as ex:
            return JsonResponse({"result": "bad", "mensaje": f"Error al obtener los datos. {ex}"})
    return JsonResponse({"result": "bad", "mensaje": "Acción no válida."}, status=400)
