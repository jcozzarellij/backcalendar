"""Health check liviano para balanceadores y supervisión externa.

GET /health/ → 200 si la BD responde; 503 si falla. No requiere autenticación.
"""
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.funciones import rate_limit


@csrf_exempt
@rate_limit(limit=60, seconds=60)
def health_view(request):
    estado = {'db': False}
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        estado['db'] = True
    except Exception:
        estado['db'] = False
    ok = estado['db']
    return JsonResponse({'ok': ok, **estado}, status=200 if ok else 503)
