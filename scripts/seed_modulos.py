"""Siembra/reorganiza modulos del sidebar, grupos y usuarios base.

Reemplaza al viejo management command `seed_modulos`. Es un script de
ejecucion manual (no se corre via manage.py) -- ver RUNBOOK_base_agents.md.

Idempotente. Por defecto UNIFICA (merge) sin borrar:
  - `Modulo`: get_or_create por `url`. Actualiza nombre/orden si cambian.
    Nunca se elimina.
  - `ModuloGrupo`: get_or_create por `nombre`. El M2M hace UNION con los
    modulos ya asignados (no pierde vinculos manuales agregados por UI).
  - `GroupModulo` del grupo `Administrador`: se garantiza que exista (su pk va en
    ID_GRUPO_ADMINISTRADOR de credenciales.json) con todos los modulos del mapa.
  - is_staff + grupo Administrador para cada superusuario.

Flags opcionales:
  --authoritative  El archivo es la unica fuente de verdad. Resetea el M2M
                   de cada seccion y del Administrador a exactamente lo del mapa.
  --reset          Soft-delete (status=False) los Modulos cuya url no este
                   en el mapa. Solo tiene sentido con --authoritative.
  --purgar         Elimina de la BD los Modulos y secciones (ModuloGrupo) que
                   no estan en el mapa (restos de otros proyectos).
  --dry-run        No escribe, solo reporta el plan.
  --skip-usuarios  No toca superusuarios.

Uso:
    python scripts/seed_modulos.py                   # merge seguro (default)
    python scripts/seed_modulos.py --authoritative    # reescribe M2Ms exactos
    python scripts/seed_modulos.py --authoritative --reset
    python scripts/seed_modulos.py --purgar           # limpia restos de otros proyectos
    python scripts/seed_modulos.py --dry-run
    python scripts/seed_modulos.py --skip-usuarios
"""
import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.contrib.auth.models import Group
from django.db import transaction

from autenticacion.models import Usuario
from seguridad.models import GroupModulo, Modulo, ModuloGrupo

ADMINISTRADOR_GROUP_NAME = 'Administrador'


SECCIONES = [
    {
        'nombre':    'Agenda',
        'icono':     'fa fa-calendar-check',
        'prioridad': 10,
        'modulos': [
            ('/agenda/mi-dia/',       'Mi día',           5, 'fa-sun'),
            ('/agenda/mi-agenda/',    'Calendario',       8, 'fa-calendar'),
            ('/agenda/citas/',        'Citas',            12, 'fa-video'),
            ('/agenda/mis-turnos/',   'Horarios',         15, 'fa-clock'),
            ('/agenda/buscar/',       'Buscar',           17, 'fa-search'),
            ('/agenda/alertas/',      'Alertas',          18, 'fa-bell'),
            ('/agenda/aplicaciones/', 'Conexiones',       20, 'fa-plug'),
        ],
    },
    {
        'nombre':    'Equipo',
        'icono':     'fa fa-calendar-alt',
        'prioridad': 15,
        'modulos': [
            ('/agenda/agenda-equipo/', 'Agenda del equipo', 5, 'fa-users'),
            ('/agenda/turnos-equipo/', 'Horarios del equipo', 10, 'fa-user-clock'),
            ('/agenda/proyectos/',     'Proyectos',         20, 'fa-folder'),
            ('/agenda/equipos/',       'Equipos',           30, 'fa-people-group'),
            ('/agenda/cola/',          'Cola de solicitudes', 7, 'fa-inbox'),
            ('/agenda/solicitudes/',   'Solicitudes',       8, 'fa-columns'),
            ('/agenda/clientes/',      'Clientes',          9, 'fa-id-card'),
            ('/agenda/feriados/',      'Feriados',          40, 'fa-umbrella-beach'),
            ('/agenda/portales/',      'Portales y productos', 50, 'fa-globe'),
            ('/agenda/parametros/',    'Parámetros', 60, 'fa-sliders'),
        ],
    },
    {
        'nombre':    'Administración de usuarios',
        'icono':     'fa fa-users-gear',
        'prioridad': 20,
        'modulos': [
            ('/autenticacion/usuario/',  'Usuarios', 10, 'fa-user'),
        ],
    },
    {
        'nombre':    'Áreas geográficas',
        'icono':     'fa fa-globe',
        'prioridad': 40,
        'modulos': [
            ('/area-geografica/pais/',      'País',      10, 'fa-flag'),
            ('/area-geografica/provincia/', 'Provincia', 20, 'fa-map'),
            ('/area-geografica/ciudad/',    'Ciudad',    30, 'fa-city'),
        ],
    },
    {
        'nombre':    'Configuración',
        'icono':     'fa fa-sliders',
        'prioridad': 50,
        'modulos': [
            ('/seguridad/configuracion/',        'Configuración del sitio', 10, 'fa-gear'),
            ('/seguridad/terminosycondiciones/', 'Términos y condiciones',  20, 'fa-file-contract'),
            ('/seguridad/webpush-broadcast/',    'Notificaciones push',    40, 'fa-bullhorn'),
        ],
    },
    {
        'nombre':    'Sistemas',
        'icono':     'fa fa-gears',
        'prioridad': 70,
        'modulos': [
            ('/seguridad/grupo/',               'Roles de usuario',      10, 'fa-user-shield'),
            ('/seguridad/modulogrupo/',         'Secciones del sidebar', 20, 'fa-bars-staggered'),
            ('/seguridad/modulo/urls/',         'Mantenimiento de URLs',    30, 'fa-link'),
            ('/seguridad/arbol-de-url/',        'Árbol de URLs',         40, 'fa-sitemap'),
            ('/seguridad/arbol-de-grupos-url/', 'Árbol de grupos',       50, 'fa-diagram-project'),
            ('/seguridad/auditoria/',           'Auditoría',             60, 'fa-clipboard-list'),
            ('/seguridad/databasebackup/',      'Respaldo de la BD',             70, 'fa-database'),
            ('/seguridad/crons/',               'Tareas programadas',    80, 'fa-clock-rotate-left'),
        ],
    },
]

def log(msg):
    print(msg)


def plan():
    for s in SECCIONES:
        log(f"  [{s['prioridad']:>3}] {s['nombre']} ({s['icono']})")
        for url, nombre, orden, _ in s['modulos']:
            log(f"      {orden:>3}. {nombre:<28} {url}")


def upsert_modulos(secciones):
    """Crea o actualiza cada Modulo de `secciones`. Devuelve {url: modulo}."""
    out = {}
    creados, actualizados, reactivados = 0, 0, 0
    for sec in secciones:
        for url, nombre, orden, icono in sec['modulos']:
            mod, was_created = Modulo.objects.get_or_create(
                url=url, defaults={'nombre': nombre, 'orden': orden, 'icono': icono},
            )
            cambios = []
            if not was_created:
                if mod.icono != icono:
                    mod.icono = icono; cambios.append('icono')
                if mod.nombre != nombre:
                    mod.nombre = nombre; cambios.append('nombre')
                if mod.orden != orden:
                    mod.orden = orden; cambios.append('orden')
                if not mod.status:
                    mod.status = True; cambios.append('reactivado')
                    reactivados += 1
                if cambios:
                    mod.save()
                    actualizados += 1
            else:
                creados += 1
            out[url] = mod
    log(f'  Modulos: {creados} creados, {actualizados} actualizados, '
        f'{reactivados} reactivados, {len(out)} total.')
    return out


def upsert_secciones(secciones, modulos_por_url, authoritative):
    """Crea/actualiza ModuloGrupo. En modo merge hace UNION al M2M; en
    authoritative lo resetea a exactamente los modulos del mapa."""
    creados, actualizados = 0, 0
    total_nuevos_links = 0
    for sec in secciones:
        mg, was_created = ModuloGrupo.objects.get_or_create(
            nombre=sec['nombre'],
            defaults={'icono': sec['icono'], 'prioridad': sec['prioridad']},
        )
        cambios = []
        if not was_created:
            if mg.icono != sec['icono']:
                mg.icono = sec['icono']; cambios.append('icono')
            if mg.prioridad != sec['prioridad']:
                mg.prioridad = sec['prioridad']; cambios.append('prioridad')
            if not mg.status:
                mg.status = True; cambios.append('reactivada')
            if cambios:
                mg.save()
                actualizados += 1
        else:
            creados += 1

        modulos_del_mapa = [modulos_por_url[url] for (url, _, _, _) in sec['modulos']]
        if authoritative:
            mg.modulos.set(modulos_del_mapa)
        else:
            existentes_ids = set(mg.modulos.values_list('id', flat=True))
            nuevos = [m for m in modulos_del_mapa if m.id not in existentes_ids]
            if nuevos:
                mg.modulos.add(*nuevos)
                total_nuevos_links += len(nuevos)
    modo = 'reasignado (set)' if authoritative else f'union: +{total_nuevos_links} link(s)'
    log(f'  Secciones: {creados} creadas, {actualizados} actualizadas, '
        f'{len(secciones)} total. M2M {modo}.')


def asignar_grupo_modulos(group_name, modulos_por_url, authoritative):
    """Garantiza que exista `group_name` y su GroupModulo, y le asigna los modulos dados."""
    group, was_created = Group.objects.get_or_create(name=group_name)
    if was_created:
        log(f'  Grupo "{group_name}" no existia, se creo (pk={group.pk}).')
    gm, _ = GroupModulo.objects.get_or_create(group=group)
    if not gm.status:
        gm.status = True
        gm.save()

    modulos = list(modulos_por_url.values())
    if authoritative:
        gm.modulos.set(modulos)
        log(f'  Grupo "{group_name}" (pk={group.pk}) re-asignado (set) a {len(modulos)} modulos.')
    else:
        existentes_ids = set(gm.modulos.values_list('id', flat=True))
        nuevos = [m for m in modulos if m.id not in existentes_ids]
        if nuevos:
            gm.modulos.add(*nuevos)
        log(f'  Grupo "{group_name}" (pk={group.pk}): +{len(nuevos)} modulo(s) agregado(s).')
    return group


def desactivar_huerfanos(modulos_por_url):
    """Marca status=False los Modulos cuya url no aparece en el mapa."""
    urls_validas = set(modulos_por_url.keys())
    huerfanos = Modulo.objects.filter(status=True).exclude(url__in=urls_validas)
    n = huerfanos.count()
    if n:
        log(f'  {n} modulo(s) huerfano(s) desactivado(s):')
        for m in huerfanos:
            log(f'      - {m.url} ({m.nombre})')
        huerfanos.update(status=False)
    else:
        log('  Sin huerfanos.')


def purgar_ajenos(secciones, modulos_por_url):
    """Elimina Modulos y ModuloGrupo que no estan en el mapa (borra tambien sus vinculos M2M)."""
    nombres = {sec['nombre'] for sec in secciones}
    ajenas = ModuloGrupo.objects.exclude(nombre__in=nombres)
    for mg in ajenas:
        log(f'      - seccion {mg.nombre}')
    n_secciones = ajenas.count()
    ajenas.delete()
    ajenos = Modulo.objects.exclude(url__in=modulos_por_url.keys())
    for m in ajenos:
        log(f'      - modulo {m.url} ({m.nombre})')
    n_modulos = ajenos.count()
    ajenos.delete()
    log(f'  Purga: {n_secciones} seccion(es) y {n_modulos} modulo(s) eliminados.')


def asignar_acceso_a_superusuarios(grupo):
    """Cada superusuario queda con is_staff y dentro del grupo dado."""
    n = 0
    for usuario in Usuario.objects.filter(is_superuser=True):
        if not usuario.groups.filter(pk=grupo.pk).exists():
            usuario.groups.add(grupo)
            n += 1
        if not usuario.is_staff:
            usuario.is_staff = True
            usuario.save()
    log(f'  Superusuarios en el grupo "{grupo.name}": {n} agregado(s).')


def run(dry_run, authoritative, reset, purgar, skip_usuarios):
    total_urls = sum(len(s['modulos']) for s in SECCIONES)
    modo = 'AUTHORITATIVE (reemplaza M2Ms)' if authoritative else 'MERGE (unifica, no borra)'
    log(f'Sembrando {len(SECCIONES)} secciones / {total_urls} URLs [{modo}]...')

    if dry_run:
        log('DRY RUN - no se escribe nada.')
        plan()
        return

    with transaction.atomic():
        modulos_por_url = upsert_modulos(SECCIONES)
        upsert_secciones(SECCIONES, modulos_por_url, authoritative)
        admin_group = asignar_grupo_modulos(ADMINISTRADOR_GROUP_NAME, modulos_por_url, authoritative)
        log(f'  >> ID_GRUPO_ADMINISTRADOR en credenciales.json = {admin_group.pk}')
        if purgar:
            purgar_ajenos(SECCIONES, modulos_por_url)
        elif reset:
            desactivar_huerfanos(modulos_por_url)
        if not skip_usuarios:
            asignar_acceso_a_superusuarios(admin_group)

    log('Listo.')


def main():
    parser = argparse.ArgumentParser(description='Siembra modulos del sidebar, grupos y usuarios base.')
    parser.add_argument('--authoritative', action='store_true',
                        help='El archivo es la unica fuente de verdad: '
                             'resetea el M2M de cada seccion y del grupo Administrador.')
    parser.add_argument('--reset', action='store_true',
                        help='Soft-delete (status=False) de Modulos cuya url no este '
                             'en el mapa. Implica --authoritative.')
    parser.add_argument('--purgar', action='store_true',
                        help='Elimina de la BD los Modulos y secciones que no esten en el mapa. Implica --authoritative.')
    parser.add_argument('--dry-run', action='store_true', help='No escribe cambios, solo reporta.')
    parser.add_argument('--skip-usuarios', action='store_true',
                        help='No toca superusuarios.')
    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        authoritative=args.authoritative or args.reset or args.purgar,
        reset=args.reset,
        purgar=args.purgar,
        skip_usuarios=args.skip_usuarios,
    )


if __name__ == '__main__':
    main()
