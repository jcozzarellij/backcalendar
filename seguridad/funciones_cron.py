"""Helpers de las tareas programadas: el gancho que cada comando de cron (`manage.py backup_bd`,
`manage.py purgar_historicos`) usa para respetar el interruptor del panel y dejar su heartbeat.

- `cron_activo(clave)`: True si la tarea existe y está activa (o si no está registrada —
  fail-open: un cron sin fila no se apaga solo). Se llama al ARRANCAR el script; si devuelve
  False, el script sale sin trabajar. Así el panel apaga un cron sin tocar el crontab.
- `heartbeat_cron(clave, exito, detalle, duracion_seg)`: registra la última ejecución en la
  fila (para el panel) y en `CronLogEjecucion` (historial + aviso por correo ante fallo, vía
  `core.funciones.logCron`). Se llama al TERMINAR.
- `ejecutar_cron(clave, fn)`: envoltorio que junta las dos cosas — chequea activo, corre `fn`,
  cronometra y deja el heartbeat con el resultado. Best-effort: nunca oculta la excepción del
  trabajo real (la re-lanza tras registrarla)."""
import time
from datetime import datetime


def cron_activo(clave):
    try:
        from seguridad.models import TareaCron
        t = TareaCron.objects.filter(clave=clave, status=True).only('activo').first()
        return True if t is None else bool(t.activo)
    except Exception:
        # Fail-open: si la tabla no está lista (migración pendiente), el cron corre igual.
        return True


def heartbeat_cron(clave, *, exito, detalle='', duracion_seg=None):
    try:
        from seguridad.models import TareaCron
        TareaCron.objects.filter(clave=clave).update(
            ultima_ejecucion=datetime.now(),
            ultimo_exito=bool(exito),
            ultimo_detalle=(detalle or '')[:300],
            ultima_duracion_seg=int(duracion_seg) if duracion_seg is not None else None,
        )
    except Exception:
        pass
    try:
        from core.funciones import logCron
        nombre = clave
        try:
            from seguridad.models import TareaCron
            t = TareaCron.objects.filter(clave=clave).only('nombre').first()
            nombre = t.nombre if t else clave
        except Exception:
            pass
        logCron(nombre, (detalle or 'ejecución')[:500], exito=bool(exito))
    except Exception:
        pass


def ejecutar_cron(clave, fn, *, log=print):
    """Corre `fn()` bajo el paraguas del panel: respeta el interruptor y deja heartbeat.
    Devuelve el valor de `fn` (o None si estaba apagado)."""
    if not cron_activo(clave):
        log(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] cron «{clave}» DESACTIVADO desde el panel — no se ejecuta.')
        return None
    t0 = time.monotonic()
    try:
        resultado = fn()
        heartbeat_cron(clave, exito=True, detalle='OK', duracion_seg=time.monotonic() - t0)
        return resultado
    except Exception as exc:
        heartbeat_cron(clave, exito=False, detalle=f'{type(exc).__name__}: {exc}'[:300],
                       duracion_seg=time.monotonic() - t0)
        raise
