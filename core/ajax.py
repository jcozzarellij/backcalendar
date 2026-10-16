from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from autenticacion.models import Usuario
from core.funciones import rate_limit


@method_decorator(rate_limit(limit=60, seconds=60), name='dispatch')
class ConsultasAjax(View):
    """Consultas Ajax del formulario de usuario: disponibilidad de username y documento."""

    def get(self, request, *args, **kwargs):
        accion = kwargs.get('accion', '')
        if not request.user.is_authenticated:
            return JsonResponse({'state': False, 'error': 'No autorizado.'}, status=403)
        try:
            if accion == 'consultarusername':
                username = request.GET['username'].lower()
                pk = request.GET.get('pk', '0') or 0
                # Sin `status`: valida unicidad contra TODA la tabla — el username de un usuario dado de
                # baja sigue tomado, y reutilizarlo reventaría al guardar.
                existe = Usuario.objects.filter(username=username).exclude(pk=pk).exists()
                actual = Usuario.objects.filter(pk=pk).first()
                val = actual.username if (existe and actual) else ''
                return JsonResponse({'state': existe, 'val': val, 'buscado': '"{}"'.format(username)})

            if accion == 'consultarcedula':
                documento = request.GET['documento']
                pk = request.GET.get('pk', '0') or 0
                existe = Usuario.objects.filter(documento=documento).exclude(pk=pk).exists()
                actual = Usuario.objects.filter(pk=pk).first()
                val = actual.documento if (existe and actual) else ''
                return JsonResponse({'state': existe, 'val': val, 'buscado': '"{}"'.format(documento)})

        except Exception:
            return JsonResponse({'state': False, 'error': 'No se pudo procesar la consulta.'})
        return JsonResponse({'state': False, 'error': 'Acción no válida.'}, status=400)
