# Stack técnico y dependencias — backcalendar

Fuente de verdad de versiones: `requirements.txt` y `backcalendar/settings.py`. Si este archivo y el código discrepan, manda el código.

## Backend

- **Python** 3.11 (`.venv` del proyecto).
- **Django** 5.2.17 LTS, **WSGI** únicamente (`backcalendar/wsgi.py`). Sin ASGI, Channels, Celery ni Redis.
- **PostgreSQL** vía `psycopg2-binary`. `ATOMIC_REQUESTS = False`: las escrituras de varios pasos llevan su propio `transaction.atomic()`. `CONN_MAX_AGE = 60`.
- **Locale:** `LANGUAGE_CODE = 'es-ec'`, `TIME_ZONE = 'America/Guayaquil'`, `USE_TZ = False` (fechas naive en hora local).
- **Usuario:** `AUTH_USER_MODEL = 'autenticacion.Usuario'`.
- **Cache:** `LocMemCache` (por proceso, no compartido entre workers).
- **Sesiones:** en BD, `JSONSerializer`, 30 días renovados en cada request (`SESSION_SAVE_EVERY_REQUEST`).
- **Logging:** solo consola (`LOGGING` en settings); el servidor/nginx los recoge. Filtro `core.log_filters.ScrubCredentialsFilter`.

## Librerías Python (directas)

| Paquete | Uso |
|---|---|
| `Django` | Framework |
| `psycopg2-binary` | Driver PostgreSQL |
| `for-django-projects` | `BetterForm` / `BetterModelForm` (base de `ModelFormBase`); usa `six` sin declararlo |
| `django-select2` | Campos Select2 |
| `django-cors-headers` | CORS (`CORS_URLS_REGEX = r'^/api/.*$'`) |
| `django-webpush` + `pywebpush` + `py-vapid` | Notificaciones push (`constantes_vapid.json`) |
| `cryptography` | Cifrado de campos (`core/crypto.py`, Fernet) |
| `Pillow` | Imágenes (PWA, fotos) |
| `pytz` | Zonas horarias |
| `requests` | HTTP saliente |

## Frontend (estático, sin bundler)

- Bootstrap 5.3 sobre el tema `static/assets_riz` (API `data-bs-*`).
- jQuery 3.7.1, DataTables (`static/datatables`), Select2 (`static/select2`), SweetAlert2 con sintaxis legacy (`type`, `result.value`), BlockUI, Switchery, Dropify, Fancybox v4, FullCalendar (`static/assets/plugins/fullcalendar`).
- Rutas absolutas `/static/...`; CSS por app en `static/css/<app>/` con `?v` de cache-busting (global: `VERSION_CSS` en settings).

## Correo

`core/correos.py` (`armar` + `despachar`, hilo con cupo) y `core/email_config.py` (`send_html_mail`). SMTP propio (`USAR_SENDGRID=false` + `SMTP_*`) o SendGrid, según `credenciales.json`.

## Tareas programadas

`seguridad.TareaCron` + management commands + crontab del servidor (`seguridad/funciones_cron.ejecutar_cron`). No hay cola de tareas.

## Configuración runtime

`credenciales.json` (no versionado; claves en `credenciales_template.json`) y `constantes_vapid.json`.
