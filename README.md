# backcalendar

Backend Django 5.2 (WSGI + PostgreSQL) con la base de la plataforma: usuarios, roles y menú, configuración del sitio, áreas geográficas, auditoría, notificaciones push y tareas programadas.

## Apps

- `core/` — `ModeloBase`, middleware, utilidades y despacho de correo.
- `autenticacion/` — `Usuario` (`AUTH_USER_MODEL`), perfil, login.
- `seguridad/` — módulos, roles, configuración, auditoría, backups, crons, notificaciones.
- `area_geografica/` — país, provincia, ciudad.
- `public/` — login, recuperación de clave y páginas legales.
- `pwa/` — manifest, service worker y web push.

## Puesta en marcha

1. `python -m venv .venv` y `pip install -r requirements.txt`.
2. Copiar `credenciales_template.json` a `credenciales.json` y completar los datos de PostgreSQL, correo y `SECRET_KEY`.
3. `python manage.py migrate`.
4. Seeders: `python scripts/seed_modulos.py`, `python scripts/seed_ecuador_geo.py`, y por shell `scripts/seed_configuracion.py` y `scripts/seed_crons_mantenimiento.py`.

## Google Calendar (conexión por usuario)

Cada persona del equipo conecta su propio Google Calendar desde **Agenda → Conexiones** (OAuth; el token de renovación se guarda cifrado). Para habilitarlo hace falta un cliente OAuth en Google Cloud:

1. En [Google Cloud Console](https://console.cloud.google.com/) crear un proyecto (por ejemplo «Turno») y habilitar **Google Calendar API** (APIs y servicios → Biblioteca).
2. **Pantalla de consentimiento OAuth**: tipo de usuario **Interno** si todas las cuentas son del Google Workspace de la empresa (sin verificación de Google ni vencimiento del token a los 7 días). Si hay cuentas Gmail externas, tipo Externo y publicar la app.
3. Permisos (scopes) que pide Turno: `calendar.events`, `calendar.freebusy`, `calendar.calendarlist.readonly`, `openid`, `userinfo.email`.
4. **Credenciales → Crear credenciales → ID de cliente OAuth → Aplicación web**. En «URI de redirección autorizados» poner exactamente `https://<dominio>/agenda/aplicaciones/google/` y, para iniciar sesión con Google, `https://<dominio>/login/google/callback/` (en desarrollo, las mismas rutas sobre `http://127.0.0.1:8008`). `<dominio>` es el de `BACKEND_PUBLIC_URL`.
5. Cargar el ID y el secreto en **Configuración del sitio → Conexión Google** (el secreto se guarda cifrado). La pestaña muestra las URIs exactas que hay que registrar. Para el login con Google, activar ahí «Permitir inicio de sesión con Google» y cargar los dominios en **Dominios de correo**.
6. En «Conexiones» aparece el botón **Conectar con Google**; «Probar conexión» verifica el acceso al calendario.

La página de inicio (`/`) toma de **Configuración → Identidad gráfica** el logo, el favicon y el **Fondo de la portada** (foto ancha detrás del título; sin foto el hero queda en azul). Los botones «Agendar cita» llevan a `/agendar/<producto>/`.

Seeders de la agenda: `python scripts/seed_roles_agenda.py` (roles Líder general, Líder de equipo, Coordinador y Miembro), `python scripts/seed_parametros_agenda.py`, `python scripts/seed_feriados_ecuador.py`, `python scripts/seed_portal_ejemplo.py` y, para que el portal tenga horarios de ejemplo, `python scripts/seed_turnos_equipo.py` (semana tipo lunes a viernes para los miembros de equipo). Pruebas: `python manage.py test agenda`.

## Portal público y recordatorios

- El cliente agenda en `/agendar/<producto>/` sin cuenta; recibe un correo con el enlace de su cita (`/cita/<token>/`, para cambiarla o cancelarla) y su enlace personal (`/conectar/<portal>/<token>/`, todas sus citas). Los enlaces son tokens con vencimiento (solo se guarda el hash). Cada producto necesita un **equipo que atiende** con al menos un responsable con turnos declarados; si no, el portal ofrece «pedir que le llamen» y la solicitud entra en la cola (`/agenda/solicitudes/`).
- Los tiempos (duración, antelación, ventana, margen) salen de **Equipo → Parámetros** y cada producto puede ajustarlos en **Portales y productos**, donde también está el enlace y el QR de cada producto.
- Crons de la agenda (registrarlos en el panel con `python manage.py shell -c "exec(open('scripts/seed_crons_mantenimiento.py', encoding='utf-8').read())"` y ponerlos en el crontab):
  - `python manage.py recordatorios_citas` cada 15 min — recordatorios al cliente (horas en Parámetros, por defecto 24 h y 1 h antes).
  - `python manage.py avisos_citas` cada 5 min — alerta «tu cita empieza pronto» (notificación y push) al equipo.
  - `python manage.py reconciliar_google` cada hora — reintenta citas sin evento y refleja lo borrado/movido en Google Calendar.
  - `python manage.py mantenimiento_agenda` diario — anonimiza IPs de reservas viejas y revoca enlaces vencidos.
- Incrustar el portal en otro sitio: en **Equipo → Portales y productos → Incrustar** está el código (`<iframe>` o botón). Solo funciona en los dominios listados en «Sitios donde se puede incrustar» del portal.
- Alertas: cada persona elige en **Alertas** cuántos minutos antes avisarle y por qué canal; la alerta flotante aparece en cualquier pantalla del panel. «Buscar» encuentra clientes, citas y solicitudes.
- La agenda vive en su propio micrositio (`/agenda/...`, barra lateral propia); desde ahí «Panel de administración» vuelve al panel general (usuarios, grupos, configuración del sistema). Textos del portal en tres idiomas: `python scripts/seed_textos_portal.py` (editables luego en la tabla `TextoPortal`).

## Restaurar el backup de base

El dump `backups/backup_20261008_122132.backup` (formato custom, pg_dump 16) se restaura con un cliente PostgreSQL 16 o superior:

```
createdb -U postgres backcalendar
pg_restore -U postgres -d backcalendar --no-owner --no-privileges backups/backup_20261008_122132.backup
psql -U postgres -d backcalendar -f scripts/limpiar_bd_cne.sql
```

`limpiar_bd_cne.sql` borra las tablas y registros de las apps eliminadas y lista las migraciones registradas de `autenticacion`, `seguridad` y `area_geografica`.
