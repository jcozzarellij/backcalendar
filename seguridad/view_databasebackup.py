"""Backups de la base de datos: generar, listar, descargar y eliminar respaldos reales.

Los archivos viven en MEDIA_ROOT/backups/<año>/<mes>/<día>/backup_<fecha>_<hora>.tar. La
descarga y el borrado pasan por esta vista con login + módulo. El respaldo lo genera
`seguridad/management/commands/backup_bd.py` (pg_dump con fallback a dumpdata) y la
rotación conserva los más nuevos. Para automatizarlo: cron / Programador de tareas
apuntando a `python manage.py backup_bd`.
"""
import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.shortcuts import render

from core.funciones import addData, secure_module, log

_RUTA_BACKUP_RE = re.compile(r'^\d{4}/\d{2}/\d{2}/backup_[\w\-]+\.tar$')


def _archivo_seguro(relativo):
    """Path del backup SOLO si la ruta relativa es válida (sin traversal)."""
    from seguridad.management.commands.backup_bd import dir_backups
    relativo = (relativo or '').strip().replace('\\', '/')
    if not _RUTA_BACKUP_RE.match(relativo):
        return None
    raiz = dir_backups().resolve()
    ruta = (raiz / relativo).resolve()
    if raiz not in ruta.parents:
        return None
    return ruta if ruta.is_file() else None


@login_required
@secure_module
def databaseBackupView(request):
    from seguridad.management.commands.backup_bd import (
        RETENCION_DEFAULT, crear_backup, listar_backups, metodo_backup, rotar_backups,
    )

    data = {
        'titulo': 'Backups de la base de datos',
        'modulo': 'Seguridad',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)

    if request.method == 'POST':
        action = request.POST.get('action') or ''
        if action == 'crear':
            try:
                destino, metodo = crear_backup()
                rotar_backups(RETENCION_DEFAULT)
            except Exception as ex:
                return JsonResponse([{'error': True, 'message': f'No se pudo generar el backup: {str(ex)[:300]}'}], safe=False)
            log(f'Generó un backup de la base de datos ({metodo}): {destino.name}', request, 'add')
            return JsonResponse([{'error': False, 'message': f'Backup generado: {destino.name}', 'reload': True}], safe=False)

        if action == 'eliminar':
            ruta = _archivo_seguro(request.POST.get('nombre'))
            if not ruta:
                return JsonResponse([{'error': True, 'message': 'Backup no encontrado.'}], safe=False)
            try:
                ruta.unlink()
            except OSError:
                return JsonResponse([{'error': True, 'message': 'No se pudo eliminar el archivo del disco.'}], safe=False)
            log(f'Eliminó el backup {ruta.name}', request, 'del')
            return JsonResponse([{'error': False, 'message': 'Backup eliminado.', 'reload': True}], safe=False)

        return JsonResponse([{'error': True, 'message': 'Acción desconocida.'}], safe=False)

    if request.GET.get('action') == 'descargar':
        ruta = _archivo_seguro(request.GET.get('nombre'))
        if not ruta:
            return JsonResponse({'error': True, 'message': 'Backup no encontrado.'}, status=404)
        log(f'Descargó el backup {ruta.name}', request, 'view')
        return FileResponse(open(ruta, 'rb'), as_attachment=True, filename=ruta.name)

    backups = []
    for b in listar_backups():
        mb = b['bytes'] / (1024 * 1024)
        backups.append({
            'nombre': b['nombre'],
            'relativo': b['relativo'],
            'tamano': f'{mb:.1f} MB' if mb >= 1 else f'{b["bytes"] / 1024:.0f} KB',
            'fecha': b['fecha'].strftime('%d/%m/%Y %H:%M'),
            'metodo': metodo_backup(b['ruta']),
        })
    data['backups'] = backups
    data['retencion'] = RETENCION_DEFAULT
    return render(request, 'seguridad/databasebackup/listado.html', data)
