"""Vista previa de los correos de una cita (cliente y líder: agendada, reprogramada y cancelada).

No envía nada ni escribe en la base: reemplaza el envío, la notificación interna y la emisión de enlaces
por versiones de prueba y guarda cada correo como HTML en `.playwright-mcp/correos/`.

    python scripts/previsualizar_correos_cita.py QW-HK45-T7
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.template.loader import get_template

from agenda import funciones_avisos_cita
from agenda.models import Cita

SALIDA = RAIZ / '.playwright-mcp' / 'correos'


def run(codigo):
    cita = Cita.objects.get(codigo=codigo)
    SALIDA.mkdir(parents=True, exist_ok=True)
    enviados = []

    def capturar(asunto, plantilla, datos, para, copia, *args, adjuntosrender=None, **kwargs):
        html = get_template(plantilla).render(datos)
        nombre = f'{len(enviados) + 1:02d}-{Path(plantilla).stem}.html'
        for adjunto in adjuntosrender or []:
            if adjunto.get('cid'):
                archivo = f'{Path(nombre).stem}-{adjunto["filename"]}'
                (SALIDA / archivo).write_bytes(adjunto['content'])
                html = html.replace(f'cid:{adjunto["cid"]}', archivo)
        (SALIDA / nombre).write_text(html, encoding='utf-8')
        enviados.append((nombre, asunto, para))

    funciones_avisos_cita.send_html_mail = capturar
    funciones_avisos_cita.notificacion = lambda *args, **kwargs: None
    funciones_avisos_cita.funciones_tokens.emitir = lambda *args, **kwargs: 'enlace-de-ejemplo'
    anterior_inicio, anterior_fin = cita.inicio - timedelta(days=2), cita.fin - timedelta(days=2)
    funciones_avisos_cita.avisar_reserva(cita.pk, f'https://ejemplo/cita/{codigo}/', 'https://ejemplo/conectar/')
    funciones_avisos_cita.avisar_reprogramacion(cita.pk, anterior_inicio, anterior_fin, por_cliente=True)
    funciones_avisos_cita.avisar_cancelacion(cita.pk, por_cliente=False)
    for nombre, asunto, para in enviados:
        print(f'{nombre}  →  {para}  ·  {asunto}')
    print(f'Listo: {SALIDA}')


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else Cita.objects.filter(status=True).order_by('-pk').first().codigo)
