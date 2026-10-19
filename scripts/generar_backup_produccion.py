"""Genera un backup LIMPIO para levantar producción, sin tocar la base local.

Pasos:
1. `pg_dump` de la base local dentro del contenedor Docker de Postgres.
2. Lo restaura en una base temporal (`<base>_limpieza_tmp`) y la limpia ahí.
3. `pg_dump` de la temporal → `media/backups/backcalendar_<fecha>.backup` (restaurar con pg_restore).
4. Borra la base temporal y empaqueta `media/` → `media/backups/backcalendar_media_<fecha>.zip`.

Qué queda: usuario `admin` (correo admin@localhost.com, misma contraseña), roles y menú, catálogos
geográficos, feriados, parámetros, crons, dominios de correo, textos del portal, proyectos, equipos
(sin miembros ni líderes), portales y productos, y la configuración del sitio sin claves OAuth.
Qué se borra: el resto de usuarios, turnos, citas y clientes, reuniones, conexiones y tokens, logs,
auditoría, sesiones, notificaciones, push, `django_migrations` y las tablas huérfanas `agents_cne_*`.

Idempotente sobre la base local (solo lee). Cada corrida genera archivos nuevos con su fecha.

Uso:
    python scripts/generar_backup_produccion.py
    python scripts/generar_backup_produccion.py --contenedor db_backcalendar
"""
import argparse
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from autenticacion.models import Usuario  # noqa: E402

USUARIO_ADMIN = 'admin'
EMAIL_ADMIN = 'admin@localhost.com'

TABLAS_A_VACIAR = [
    'agenda_actividadcita', 'agenda_avisoproximo', 'agenda_bloqueocupado', 'agenda_capturatecnica',
    'agenda_cierrecita', 'agenda_cita', 'agenda_cliente', 'agenda_conexionaplicacion',
    'agenda_enviorecordatorio', 'agenda_notacita', 'agenda_participantecita', 'agenda_preferenciaagenda',
    'agenda_solicitud', 'agenda_tokenacceso', 'agenda_reunion',
    'agenda_miembroequipo', 'agenda_franjaturno', 'agenda_patronturno', 'agenda_excepcionturno',
    'autenticacion_cuentagoogle',
    'django_admin_log', 'django_session', 'django_migrations',
    'seguridad_audiusuariotabla', 'seguridad_cronlogejecucion', 'seguridad_errorlog',
    'seguridad_notificacion', 'seguridad_sessionuser',
    'webpush_pushinformation', 'webpush_subscriptioninfo', 'webpush_group',
]

APPS_HUERFANAS = ('agents_cne', 'agents_ai', 'crm', 'monitoreo')

CARPETAS_MEDIA = ('configuracion', 'productos', 'guia', 'pwa')


def sql_limpieza():
    tablas = ', '.join(f'public.{t}' for t in TABLAS_A_VACIAR)
    apps = ', '.join(f"'{a}'" for a in APPS_HUERFANAS)
    return f"""
\\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
    t record;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables
             WHERE schemaname = 'public' AND tablename LIKE 'agents\\_cne\\_%'
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', t.tablename);
    END LOOP;
END $$;

DELETE FROM auth_group_permissions WHERE permission_id IN (
    SELECT p.id FROM auth_permission p JOIN django_content_type c ON c.id = p.content_type_id
    WHERE c.app_label IN ({apps}));
DELETE FROM autenticacion_usuario_user_permissions WHERE permission_id IN (
    SELECT p.id FROM auth_permission p JOIN django_content_type c ON c.id = p.content_type_id
    WHERE c.app_label IN ({apps}));
DELETE FROM auth_permission WHERE content_type_id IN (
    SELECT id FROM django_content_type WHERE app_label IN ({apps}));
DELETE FROM django_admin_log WHERE content_type_id IN (
    SELECT id FROM django_content_type WHERE app_label IN ({apps}));
DELETE FROM django_content_type WHERE app_label IN ({apps});

TRUNCATE {tablas} RESTART IDENTITY;

UPDATE agenda_proyecto SET lider_id = NULL;
UPDATE agenda_equipo SET lider_id = NULL, ultimo_asignado_id = NULL;

DO $$
DECLARE
    admin_id integer;
    fk record;
BEGIN
    SELECT id INTO admin_id FROM autenticacion_usuario WHERE username = '{USUARIO_ADMIN}';
    IF admin_id IS NULL THEN
        RAISE EXCEPTION 'No existe el usuario {USUARIO_ADMIN}';
    END IF;
    FOR fk IN
        SELECT cl.relname AS tabla, att.attname AS columna, att.attnotnull AS obligatoria
        FROM pg_constraint con
        JOIN pg_class cl ON cl.oid = con.conrelid
        JOIN pg_namespace ns ON ns.oid = cl.relnamespace
        JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1]
        WHERE con.contype = 'f' AND ns.nspname = 'public'
          AND con.confrelid = 'public.autenticacion_usuario'::regclass
          AND cl.relname <> 'autenticacion_usuario'
    LOOP
        IF fk.obligatoria THEN
            EXECUTE format('DELETE FROM public.%I WHERE %I <> %s', fk.tabla, fk.columna, admin_id);
        ELSE
            EXECUTE format('UPDATE public.%I SET %I = NULL WHERE %I <> %s', fk.tabla, fk.columna, fk.columna, admin_id);
        END IF;
    END LOOP;
    UPDATE autenticacion_usuario SET usuario_creacion_id = NULL WHERE usuario_creacion_id <> admin_id;
    UPDATE autenticacion_usuario SET usuario_modificacion_id = NULL WHERE usuario_modificacion_id <> admin_id;
    DELETE FROM autenticacion_usuario WHERE id <> admin_id;
    UPDATE autenticacion_usuario
       SET email = '{EMAIL_ADMIN}', is_superuser = TRUE, is_staff = TRUE, is_active = TRUE, status = TRUE
     WHERE id = admin_id;
END $$;

UPDATE seguridad_configuracion
   SET google_client_id = '', google_client_secret = '', google_redirect_uri = '', conexion_google = FALSE,
       teams_client_id = '', teams_client_secret = '', teams_tenant_id = '', teams_redirect_uri = '',
       zoom_client_id = '', zoom_client_secret = '', zoom_redirect_uri = '',
       pg_dump_cmd = NULL;

COMMIT;

SELECT 'usuarios', count(*) FROM autenticacion_usuario
UNION ALL SELECT 'grupos', count(*) FROM auth_group
UNION ALL SELECT 'modulos', count(*) FROM seguridad_modulo
UNION ALL SELECT 'proyectos', count(*) FROM agenda_proyecto
UNION ALL SELECT 'equipos', count(*) FROM agenda_equipo
UNION ALL SELECT 'portales', count(*) FROM agenda_portal
UNION ALL SELECT 'productos', count(*) FROM agenda_producto
UNION ALL SELECT 'feriados', count(*) FROM agenda_feriado
UNION ALL SELECT 'ciudades', count(*) FROM area_geografica_ciudad
UNION ALL SELECT 'citas', count(*) FROM agenda_cita
UNION ALL SELECT 'tablas agents_cne', count(*) FROM pg_tables WHERE tablename LIKE 'agents\\_cne\\_%';
"""


def ejecutar(comando, entrada=None):
    resultado = subprocess.run(comando, input=entrada, capture_output=True, text=True, encoding='utf-8')
    if resultado.returncode != 0:
        raise RuntimeError(f'Falló: {" ".join(comando[:4])}...\n{resultado.stderr.strip()}')
    return resultado.stdout


def empaquetar_media(destino):
    media = Path(settings.MEDIA_ROOT)
    admin = Usuario.objects.filter(username=USUARIO_ADMIN).first()
    extras = [media / admin.foto.name] if admin and admin.foto else []
    total = 0
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as paquete:
        for carpeta in CARPETAS_MEDIA:
            for archivo in sorted((media / carpeta).rglob('*')):
                if archivo.is_file():
                    paquete.write(archivo, archivo.relative_to(media).as_posix())
                    total += 1
        for archivo in extras:
            if archivo.is_file():
                paquete.write(archivo, archivo.relative_to(media).as_posix())
                total += 1
    return total


def main():
    parser = argparse.ArgumentParser(description='Backup limpio para producción.')
    parser.add_argument('--contenedor', default='db_backcalendar', help='Contenedor Docker de Postgres.')
    args = parser.parse_args()

    base = settings.DATABASES['default']
    usuario_bd, nombre_bd = base['USER'], base['NAME']
    temporal = f'{nombre_bd}_limpieza_tmp'
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino_dir = Path(settings.MEDIA_ROOT) / 'backups'
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino_backup = destino_dir / f'backcalendar_{marca}.backup'
    destino_zip = destino_dir / f'backcalendar_media_{marca}.zip'
    docker = ['docker', 'exec', '-i', args.contenedor]
    origen, limpio = '/tmp/backup_origen.backup', '/tmp/backup_limpio.backup'

    print(f'1/5 Copiando la base local «{nombre_bd}»...')
    ejecutar(docker + ['pg_dump', '-U', usuario_bd, '-Fc', '-d', nombre_bd, '-f', origen])
    try:
        print(f'2/5 Restaurando en la base temporal «{temporal}»...')
        ejecutar(docker + ['dropdb', '-U', usuario_bd, '--if-exists', temporal])
        ejecutar(docker + ['createdb', '-U', usuario_bd, temporal])
        ejecutar(docker + ['pg_restore', '-U', usuario_bd, '-d', temporal, '--no-owner', origen])

        print('3/5 Limpiando la copia temporal...')
        salida = ejecutar(docker + ['psql', '-U', usuario_bd, '-d', temporal, '-q', '-tA', '-F', ': '],
                          entrada=sql_limpieza())
        for linea in salida.strip().splitlines():
            print(f'    {linea}')

        print(f'4/5 Generando {destino_backup.name}...')
        ejecutar(docker + ['pg_dump', '-U', usuario_bd, '-Fc', '-d', temporal, '-f', limpio])
        ejecutar(['docker', 'cp', f'{args.contenedor}:{limpio}', str(destino_backup)])
    finally:
        subprocess.run(docker + ['dropdb', '-U', usuario_bd, '--if-exists', temporal], capture_output=True)
        subprocess.run(docker + ['rm', '-f', origen, limpio], capture_output=True)

    print(f'5/5 Empaquetando media en {destino_zip.name}...')
    archivos = empaquetar_media(destino_zip)
    print(f'Listo.\n    {destino_backup} ({destino_backup.stat().st_size / 1048576:.1f} MB)'
          f'\n    {destino_zip} ({destino_zip.stat().st_size / 1048576:.1f} MB, {archivos} archivos)')


if __name__ == '__main__':
    main()
