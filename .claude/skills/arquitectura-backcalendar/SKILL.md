---
name: arquitectura-backcalendar
description: Método de arquitectura de backcalendar — dónde va cada pieza (app, view_<recurso>.py, templates/<app>/<recurso>/, funciones_*.py, urls), reglas de modelos (ModeloBase, RegistroInmutable), acceso (Usuario.is_staff + GroupModulo) y el flujo spec → grilling → implementar. Usar al diseñar una feature nueva, una app nueva o al decidir dónde ubicar código.
---

# Arquitectura backcalendar

Hechos del sistema y método para ubicar código nuevo. `CLAUDE.md` manda; esta skill lo ordena para diseñar. Implementación concreta: skills `django-backend`, `formmodal`, `design-guidelines-panel`.

## El sistema en una mirada

- Monolito Django 5.2, **WSGI** (`backcalendar/wsgi.py`), PostgreSQL, sin Celery/Redis/Channels. Lo asíncrono es: hilo acotado para correo (`core/correos.py::despachar`) y crons registrados en `TareaCron` (`seguridad/funciones_cron.py::ejecutar_cron`).
- `ATOMIC_REQUESTS = False`: la transacción la abre cada POST con `transaction.atomic()`.
- `USE_TZ = False`, `TIME_ZONE = 'America/Guayaquil'`: fechas naive locales.
- `AUTH_USER_MODEL = "autenticacion.Usuario"` (`AbstractUser` + `ModeloBase`).
- Apps: `core` (bases y helpers, sin modelos de negocio), `autenticacion` (usuario, login, perfil), `seguridad` (módulos, roles, configuración, auditoría, notificaciones, crons, backups), `area_geografica` (catálogo país/provincia/ciudad), `public` (login y páginas públicas), `pwa` (manifest, service worker, push).

## Acceso y alcance

- Al panel entra `Usuario.is_staff`; superusuario ve todo.
- El alcance son los **grupos** de Django: `GroupModulo` (OneToOne con `Group`) lista los `Modulo` (URL) que ese rol puede abrir; `ModuloGrupo` agrupa módulos en secciones del sidebar.
- `@secure_module` (`core/funciones.py`) compara `request.path` contra las URLs de los módulos del usuario. Una pantalla nueva no se ve hasta que su URL es un `Modulo` asignado a un rol: sembrarla en `SECCIONES` de `scripts/seed_modulos.py` (idempotente) o registrarla desde «Mantenimiento de Url» → extraer URLs (`seguridad/view_modulos_sistema.py`).
- Pantallas de plataforma (no de un rol operativo): además `@solo_administrador` (superusuario o grupo `ID_GRUPO_ADMINISTRADOR`).
- No hay modelos de perfil: no crear `Perfil*` para dar acceso; se usa grupo + módulo.

## Dónde va cada cosa

| Pieza | Ubicación |
|---|---|
| Vista de un recurso | `<app>/view_<recurso>.py`, una función `<recurso>View` con dispatch `if action` |
| Fragmento del modal | `templates/<app>/<recurso>/form.html` |
| Listado | `templates/<app>/<recurso>/listado.html` (extiende `base.html`) |
| Detalle de solo lectura | `templates/<app>/<recurso>/detalle.html` o acción GET `ver` |
| Formularios | `<app>/forms.py` (`ModelFormBase` / `FormBase`) |
| Lógica de dominio reutilizable | `<app>/funciones_<tema>.py` (ej. `autenticacion/funciones_autenticacion.py`) |
| Helper genérico (texto, fechas, archivos) | `core/funciones.py` o `core/funciones_adicionales.py`; buscar antes de crear |
| Consulta AJAX transversal | rama en `core/ajax.py::ConsultasAjax` → `/ajaxrequest/<accion>` |
| CSS de la pantalla | `static/css/<app>/<pantalla>.css` |
| Seeders, CLIs, demos | `scripts/` en la raíz, nunca dentro de una app; bootstrap con `Path(__file__).resolve().parents[1]` |
| Correo | plantilla en `templates/email/`, envío con `core.correos.armar` + `despachar` |
| Tarea periódica | función de dominio + `TareaCron` (ver `seguridad/adm_crons.py`) |

Una vista nunca define funciones helper de acción sueltas: el CRUD va inline en su rama; lo que se repite es dominio y va a `funciones_*.py`.

## Registro de URLs

Cada app expone una tupla de dicts en `<app>/urls.py` y genera sus `urlpatterns` en loop:

```python
from django.urls import re_path

from .view_reserva import reservaView

agendamiento_urls = (
    {
        "nombre": "Reservas",
        "url": 'reserva/',
        "vista": reservaView,
    },
)

urlpatterns = []
for u in agendamiento_urls:
    urlpatterns.append(re_path(r'^{}$'.format(u["url"]), u["vista"]))
```

Una app nueva se suma a `urls_sistema` en `backcalendar/urls.py` con `nombre`, `url` (minúsculas con guiones), `sub_urls`, `include`, `name: None`, `vista: None`, y a `INSTALLED_APPS`. `urls_sistema` también alimenta la extracción de módulos, así que la URL final es `/<url de la app><url del recurso>`. Opcional: `"grupo"` en el dict del recurso para agruparlo en la vista previa de extracción.

## Modelos

- **Todo modelo nuevo hereda `core.custom_models.ModeloBase`** (`usuario_creacion`, `fecha_registro`, `usuario_modificacion`, `fecha_modificacion`, `status`). No redeclarar esas columnas con otro nombre.
- Borrado = `status=False` + `save(request)`. Lecturas con `status=True`; en `get_or_create` sobre clave única, `status` va en `defaults`.
- **Evidencia** (lo que no debe editarse ni borrarse una vez escrito): `core.custom_models.RegistroInmutable`. Ledgers/logs append-only con `models.Model` solo los existentes (`ErrorLog`, `AudiUsuarioTabla`, `CronLogEjecucion`, `SessionUser`); una excepción nueva se pide.
- Choices como constantes de módulo; textos largos en tabla + seeder, no en dicts en código.
- Archivos con `FileExtensionValidator` + validador de tamaño de `core/validadores.py`.
- `activo` (pausa) y `status` (baja lógica) son cosas distintas y pueden convivir.
- Migraciones: solo nuevas y aditivas; nunca editar una existente.

## Método para una feature nueva

1. **Spec** — skill `spec`: abre `specs/<área>/YYYY-MM-DD-<nombre>.md` y conduce la conversación.
2. **Grilling** — skill `grilling`: rondas de preguntas con recomendación hasta tener archivos, primer/último paso y observable de verificación.
3. **Diseño** — decidir con esta tabla: ¿app existente o nueva? ¿recurso nuevo (vista + templates) o acción nueva en una vista que ya existe? Por defecto, acción nueva antes que tocar un `add`/`change` que funciona. ¿Qué es dominio (va a `funciones_*.py`) y qué es CRUD (inline)?
4. **Implementar** — `django-backend` + `formmodal` (+ `formmodal-data-preview`, `batch-process`, `inline-ajax-autosave` según el caso) y `design-guidelines-panel` para la UI; `/crud-simple` para un CRUD de catálogo.
5. **Revisión del usuario** — el desarrollador corre el servidor en PyCharm.
6. **Verificación a fondo** si toca la lista de `CLAUDE.md`: migraciones que van a producción, autenticación/gates de seguridad, registros de evidencia, contabilidad. Leer el código real de la API usada y probar casos borde.
7. **Revisión de reglas** — agente `revisor-reglas` sobre el diff, si el usuario lo pide.

## Criterios al decidir

- Datos consistentes > comodidad: preferir restricciones en base (`UniqueConstraint` con `condition=Q(status=True)`, `CheckConstraint`) a validaciones solo en el form.
- Error imposible > error manejado: una acción que no debe repetirse se diseña idempotente.
- Trazabilidad: toda escritura deja `log(...)`; cambios sensibles, `salva_auditoria(...)` con antes y después.
- Profundidad: un `funciones_*.py` con pocas funciones de interfaz chica y mucho comportamiento detrás vale más que muchos helpers finos (vocabulario en la skill `codebase-design`).
