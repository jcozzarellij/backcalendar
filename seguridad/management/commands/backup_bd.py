"""Backup real de la base de datos con rotación.

Genera un respaldo en MEDIA_ROOT/backups/<año>/<mes>/<día>/backup_<fecha>_<hora>.tar:

- Con `pg_dump` disponible (PATH o setting/credencial PG_DUMP_CMD): formato tar de
  Postgres (`pg_dump -Ft`), restaurable con pg_restore.
- Sin pg_dump (ej. equipo de desarrollo): fallback a `dumpdata` de Django empaquetado en
  el tar como `datos.json`, restaurable con loaddata.

Rotación: conserva los N respaldos más nuevos (default 15), borra el resto y elimina las
carpetas de fecha que quedan vacías.

Uso:
    python manage.py backup_bd
    python manage.py backup_bd --retencion 30

Programarlo diario (cron / Programador de tareas de Windows) apuntando a este comando.
"""
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

RETENCION_DEFAULT = 15
PREFIJO = 'backup_'
EXTENSION = '.tar'


def dir_backups():
    """Raíz de los respaldos."""
    ruta = Path(settings.MEDIA_ROOT) / 'backups'
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def dir_backup_fecha(momento=None):
    """Carpeta <año>/<mes>/<día> del respaldo, creada si no existe."""
    momento = momento or datetime.now()
    ruta = dir_backups() / momento.strftime('%Y') / momento.strftime('%m') / momento.strftime('%d')
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def metodo_backup(ruta):
    """'pg_dump' o 'dumpdata' según el primer miembro del tar."""
    try:
        with tarfile.open(ruta, 'r') as paquete:
            primero = paquete.next()
    except (tarfile.TarError, OSError):
        return 'desconocido'
    nombre = primero.name if primero else ''
    return 'pg_dump' if nombre.endswith('toc.dat') else 'dumpdata'


def listar_backups():
    """Respaldos existentes, más nuevos primero:
    [{'nombre', 'relativo', 'ruta', 'bytes', 'fecha'}]."""
    raiz = dir_backups()
    archivos = []
    for f in raiz.rglob(f'{PREFIJO}*{EXTENSION}'):
        if not f.is_file():
            continue
        st = f.stat()
        archivos.append({
            'nombre': f.name,
            'relativo': f.relative_to(raiz).as_posix(),
            'ruta': f,
            'bytes': st.st_size,
            'fecha': datetime.fromtimestamp(st.st_mtime),
        })
    archivos.sort(key=lambda a: a['fecha'], reverse=True)
    return archivos


def _pg_dump_cmd():
    # Prioridad: tabla Configuracion → settings (credenciales.json) → PATH.
    configurado = ''
    try:
        from seguridad.models import Configuracion
        conf = Configuracion.get_instancia()
        configurado = (getattr(conf, 'pg_dump_cmd', '') or '').strip()
    except Exception:
        configurado = ''
    if not configurado:
        configurado = (getattr(settings, 'PG_DUMP_CMD', '') or '').strip()
    if configurado and Path(configurado).exists():
        return configurado
    return shutil.which('pg_dump')


def crear_backup():
    """Genera un respaldo nuevo y devuelve (ruta, metodo). Lanza CommandError si falla."""
    db = settings.DATABASES['default']
    momento = datetime.now()
    fecha = momento.strftime('%Y%m%d_%H%M%S')
    destino_dir = dir_backup_fecha(momento)
    destino = destino_dir / f'{PREFIJO}{fecha}{EXTENSION}'

    pg_dump = _pg_dump_cmd()
    if pg_dump and 'postgresql' in (db.get('ENGINE') or ''):
        env = dict(os.environ)
        if db.get('PASSWORD'):
            env['PGPASSWORD'] = db['PASSWORD']
        comando = [
            pg_dump, '-Ft',
            '-h', db.get('HOST') or 'localhost',
            '-p', str(db.get('PORT') or 5432),
            '-U', db.get('USER') or 'postgres',
            '-f', str(destino),
            db.get('NAME') or '',
        ]
        try:
            proceso = subprocess.run(comando, env=env, capture_output=True, text=True, timeout=1800)
        except (OSError, subprocess.TimeoutExpired) as ex:
            raise CommandError(f'pg_dump no se pudo ejecutar: {ex}')
        if proceso.returncode != 0:
            destino.unlink(missing_ok=True)
            raise CommandError(f'pg_dump falló: {(proceso.stderr or "")[:500]}')
        return destino, 'pg_dump'

    temporal = destino_dir / f'{PREFIJO}{fecha}.json.tmp'
    try:
        with open(temporal, 'w', encoding='utf-8') as salida:
            call_command(
                'dumpdata',
                exclude=['contenttypes', 'auth.permission', 'sessions.session'],
                natural_foreign=True, natural_primary=True, stdout=salida,
            )
        with tarfile.open(destino, 'w') as paquete:
            paquete.add(temporal, arcname='datos.json')
    except Exception as ex:
        destino.unlink(missing_ok=True)
        raise CommandError(f'dumpdata falló: {ex}')
    finally:
        temporal.unlink(missing_ok=True)
    return destino, 'dumpdata'


def _retencion_configurada():
    try:
        from seguridad.models import Configuracion
        valor = getattr(Configuracion.get_instancia(), 'backup_retencion', 0) or 0
        if int(valor) > 0:
            return int(valor)
    except Exception:
        pass
    return RETENCION_DEFAULT


def _limpiar_carpetas_vacias():
    """Borra las carpetas de fecha que quedaron sin respaldos (de la más profunda a la raíz)."""
    raiz = dir_backups()
    carpetas = sorted(
        (d for d in raiz.rglob('*') if d.is_dir()),
        key=lambda d: len(d.parts), reverse=True,
    )
    for carpeta in carpetas:
        try:
            carpeta.rmdir()
        except OSError:
            pass


def rotar_backups(retencion=None):
    """Borra los respaldos que exceden la retención (tabla Configuracion → default).
    Devuelve la lista de rutas relativas borradas."""
    if retencion is None:
        retencion = _retencion_configurada()
    borrados = []
    for viejo in listar_backups()[max(retencion, 1):]:
        try:
            viejo['ruta'].unlink()
            borrados.append(viejo['relativo'])
        except OSError:
            pass
    _limpiar_carpetas_vacias()
    return borrados


class Command(BaseCommand):
    help = 'Genera un backup de la base de datos en MEDIA_ROOT/backups/<año>/<mes>/<día>/ con rotación.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retencion', type=int, default=None,
            help='Cuántos respaldos conservar. Omitido = usa Configuración '
                 f'(tabla) o el default {RETENCION_DEFAULT}.',
        )

    def handle(self, *args, **options):
        from seguridad.funciones_cron import ejecutar_cron

        def _trabajo():
            destino, metodo = crear_backup()
            borrados = rotar_backups(options['retencion'])
            tam_mb = destino.stat().st_size / (1024 * 1024)
            relativo = destino.relative_to(dir_backups()).as_posix()
            self.stdout.write(self.style.SUCCESS(
                f'Backup generado ({metodo}): {relativo} ({tam_mb:.1f} MB).'
            ))
            if borrados:
                self.stdout.write(f'Rotación: {len(borrados)} respaldo(s) viejo(s) eliminados.')

        ejecutar_cron('backup_bd', _trabajo, log=self.stdout.write)
