# Plan de construcción — Micrositio de agendas (backcalendar)

Fecha: 2026-10-08 · Estado: plan (sin implementar)

Fuentes:
- `docs/Estudio micrositio de agendas - Exducere Online.docx` (estudio de requerimientos del 8 de octubre).
- `docs/Micrositio de agendas demos de interfaz (1).html` (25 pantallas de demostración).

Este plan traduce ese estudio al código real de backcalendar: qué app nueva se crea, qué va en `public/`, qué se reutiliza de `core`, `seguridad` y `pwa`, y en qué orden se construye.

> Reemplaza a `docs/estudio_agendamiento_citas.md` en dos puntos: el acceso a Google **no** es OAuth por profesional sino **cuenta de servicio con delegación de dominio** (todos tienen Google Workspace), y **el cliente elige la hora** en portales propios por producto.

---

## 1. Qué se construye (resumen del estudio)

- **CRM de citas** de Exducere Online para unas 7 personas con Google Workspace.
- **Entrada de citas:** portales de reserva públicos propios, uno por producto o cliente, con marca propia y tres idiomas (es, en, pt). Están pensados para **personas mayores**: cuatro pasos, letra de 19 px o más, botones de 56 px y trato de «usted».
- **Motor:** turnos declarados, menos lo ocupado en Google (freebusy), menos los márgenes. La antelación es de 24 h y la ventana de reserva de 2 semanas. La regla portal + producto define el proyecto y el equipo. La cita se crea en Google Calendar con Meet y el organizador es el líder del proyecto. Si no hay espacio, la solicitud va a la cola del coordinador.
- **Cliente:** su ficha se crea sola con la primera cita. Tiene código (`C-48213`), un enlace personal «Mis citas», QR, continuidad de sesiones, y se guarda lo que dio el cliente y lo que captó el sistema.
- **Micrositio interno:**
  - Mi día, Mi agenda (calendario con arrastrar y soltar), Mis turnos, Vista de equipo, Cola, Solicitudes (tablero y tabla).
  - Página de reunión con cierre, Búsqueda global, Clientes, Portales de reserva, Centro de alertas, Configuración.
  - Versión móvil (PWA).
- **Roles:** Líder general, Líder de equipo, Coordinador y Miembro.
- **Versiones:** V1 es la etapa de reunión completa. V2 suma leads, seguimiento, proformas, reportes y el resumen desde Meet. V3 suma el correo en el CRM.

---

## 2. Decisión de estructura: una app nueva + el portal en `public/`

| Pieza | Dónde | Por qué |
|---|---|---|
| **Modelos de todo el dominio** (personas, equipos, turnos, citas, portales, productos, clientes, tokens) | **App nueva `agenda/`** | Es un dominio grande y propio; `public/` hoy no tiene modelos y debe seguir siendo solo de presentación. Un único dueño de los modelos evita dependencias cruzadas. |
| **Micrositio interno** (Mi día, agenda, turnos, cola, portales admin, clientes, configuración) | `agenda/` (vistas) + `templates/agenda/<recurso>/` + `static/css/agenda/` | Pantallas de staff con `@login_required` + `@secure_module`, patrón `if action`. |
| **Portal público de reserva** (lista de productos = landing del portal, agendar en 4 pasos, Mis citas, ventana incrustada) | **`public/portal/`** (vistas) + `templates/public/portal/` + `static/css/public/portal.css` | Lo pidió el usuario: la landing va en `public/`. Las vistas públicas importan los modelos y la lógica de `agenda`. |
| **Lógica de dominio** (disponibilidad, asignación, conector Google, tokens, QR) | `agenda/funciones_*.py` | Regla del repo: lo reutilizable va en `funciones_*.py`, nunca suelto en una vista. La comparten micrositio y portal. |
| **Tareas programadas** (recordatorios, liberar apartados, reconciliar con Google, purgar IP) | `agenda/management/commands/` + `seguridad.TareaCron` | Sin Celery ni Redis (se quitaron a propósito). Mismo mecanismo que `purgar_historicos`. |

Estructura propuesta:

```
agenda/
  models.py                 # o models/ por grupo si crece (personas, turnos, citas, portales, clientes)
  forms.py
  urls.py                   # agenda_urls (tupla), registrada en backcalendar/urls.py → urls_sistema
  funciones_disponibilidad.py
  funciones_asignacion.py
  funciones_google.py       # conector Calendar/Meet con cuenta de servicio
  funciones_tokens.py       # enlaces personales, gestión, apartado (hash + vigencia)
  funciones_clientes.py     # ficha automática, códigos, captura técnica
  funciones_qr.py
  view_mi_dia.py, view_agenda.py, view_turnos.py, view_equipo.py, view_cola.py,
  view_solicitudes.py, view_reunion.py, view_busqueda.py, view_clientes.py,
  view_portales.py, view_alertas.py, view_configuracion.py, view_personas.py
  management/commands/      # enviar_recordatorios, liberar_apartados, reconciliar_google, purgar_capturas
public/
  portal/
    view_portal.py          # landing del portal (productos) + agendar (4 pasos) + confirmar
    view_mis_citas.py       # enlace personal: ver, cambiar, cancelar, pedir otra
    view_incrustar.py       # script/iframe para sitios autorizados
  urls.py                   # rutas públicas del portal (sin login)
templates/agenda/<recurso>/{listado,form,...}.html
templates/public/portal/{base_portal,productos,agendar,mis_citas,incrustado}.html
templates/email/agenda/{cita_confirmada,recordatorio,cita_cambiada,cita_cancelada}.html
static/css/agenda/*.css, static/css/public/portal.css, static/js/agenda/*.js
```

---

## 3. Qué se reutiliza del repo (revisión de `core`, `seguridad`, `pwa`, `autenticacion`)

| Necesidad del estudio | Ya existe | Cómo se usa |
|---|---|---|
| Auditoría y soft delete en cada tabla | `core.custom_models.ModeloBase` | **Todo modelo nuevo hereda de `ModeloBase`** (ver §4). |
| Registros que no se editan (actividad de la reunión, envíos de recordatorio) | `core.custom_models.RegistroInmutable` | Para la línea de actividad y la evidencia de envíos; ver §4. |
| Formularios del micrositio | `ModelFormBase` / `FormBase` (`core.custom_models`), `FormModeloBase` / `ExtFileField` (`core.custom_forms`), `FormError` | Patrón `formmodal`. |
| Persona del equipo | `autenticacion.Usuario` (`AUTH_USER_MODEL`, `is_staff`) | La persona **es** el `Usuario`; los datos de agenda van en un perfil OneToOne (`PerfilAgenda`). No se crea una tabla «Persona» paralela. |
| Roles y alcance | Django `Group` + `seguridad.GroupModulo` + `@secure_module` | Cuatro grupos: Líder general, Líder de equipo, Coordinador, Miembro. El menú sale de `GroupModulo`; el alcance «su equipo» se filtra en las consultas. Los permisos se validan en el servidor. |
| Parámetros globales (tabla «Configuracion» del estudio) | `seguridad.ParametroSistema` (clave, valor, tipo, grupo, descripción, valor por defecto, cache 60 s) | Es exactamente esa tabla. Se agregan grupos a `PARAMETRO_GRUPO_CHOICES` (tiempos, portal, cliente, recordatorios, google) y una semilla en `scripts/`. **No** confundir con `seguridad.Configuracion` (datos del sitio: nombre, logo). |
| Secretos cifrados | `core.crypto.EncryptedTextField`, `encrypt_text` | Para lo sensible guardado en BD. ✅ La credencial JSON de la cuenta de servicio va en `credenciales.json` (decidido 2026-10-08); en BD cifrada solo lo que se genere en la app. |
| Historial de cambios de configuración y bitácora | `core.funciones.log` + `salva_auditoria` + `seguridad.AudiUsuarioTabla` | La «Bitácora» del estudio se arma sobre esto; la actividad por reunión es un modelo propio (`ActividadCita`). |
| Centro de alertas | `seguridad.Notificacion` (destinatario, url, leído, prioridad, tipo) + `core.funciones.notificacion` | Reutilizar para «Alertas»; si hace falta el objeto relacionado, se agrega un campo opcional por migración aditiva. |
| Web push | `pwa` (manifest, service worker, VAPID en `constantes_vapid.json`) + `django-webpush` + `pwa.notificaciones.enviar_push_usuario` | Ya está todo: solo se disparan los avisos de reunión. |
| App instalable y primer ingreso | `pwa` (barra de instalación, `push_optin`) | La pantalla «Primer ingreso» se apoya en esto. |
| Correo | `core.correos.armar` + `despachar` (hilo con cupo), plantillas en `templates/email/` | Confirmación, recordatorios y cambios, por idioma. |
| Tareas programadas | `seguridad.TareaCron` + `seguridad.funciones_cron.ejecutar_cron` + `scripts/seed_crons_mantenimiento.py` | Recordatorios, liberar apartados, reconciliar con Google, renovar canales y purgar la IP a los 90 días. |
| Límite contra abuso en el portal | `core.funciones.rate_limit` (con techo por IP) + `get_client_ip` | En disponibilidad, apartar y confirmar. |
| Listados y paginación | `core.funciones.paginador`, `templates/paginacion.html` | Tabla de solicitudes, clientes. |
| Validaciones | `core.validadores` (tamaño de archivo, cédula/RUC, solo números) | Logo del portal, teléfono. |
| Archivos subidos | `core.models_utils.FileNameUploadToPath`, `FileExtensionValidator` | Logo de portal. |
| Zonas horarias | `core.constantes.TIMEZONE_CHOICES` | Zona horaria del cliente y de la persona. |
| Calendario con arrastrar | FullCalendar en `static/assets/plugins/fullcalendar` | Revisar versión: el estudio asume la edición estándar MIT con elementos externos (§9). |
| Catálogo geográfico | `area_geografica` (País, Provincia, Ciudad) | Opcional: ciudad aproximada del cliente como texto o FK. |

Lo que **no** existe y hay que traer: librerías de Google (`google-auth`, `google-api-python-client`), QR (`segno`, sin dependencias), GeoIP (`geoip2` + base GeoLite2, revisar licencia), captcha y SortableJS (tableros).

---

## 4. Modelo de datos (todo `ModeloBase`)

Regla inquebrantable del repo: **cada modelo hereda de `core.custom_models.ModeloBase`**, sin repetir `fecha`, `creado_en`, `creado_por` (ya vienen como `fecha_registro`, `usuario_creacion`, etc.). Los choices van a nivel de módulo. `activo` sí puede convivir con `status`.

| Modelo | Campos clave | Base |
|---|---|---|
| `PerfilAgenda` | usuario (OneToOne `Usuario`), codigo, correo_google, zona_horaria, idiomas que atiende, aviso_previo_min, activo | ModeloBase |
| `Proyecto` | codigo, nombre, lider (FK `Usuario`), activo | ModeloBase |
| `Equipo` | proyecto, nombre, lider | ModeloBase |
| `MiembroEquipo` | equipo, usuario, rol (`ROL_MIEMBRO`: responsable / copia), obligatorio | ModeloBase · única (equipo, usuario) |
| `PatronTurno` | usuario, vigencia_desde, vigencia_hasta (nula = sin fin) | ModeloBase |
| `FranjaTurno` | patron, dia_semana, hora_inicio, hora_fin | ModeloBase |
| `ExcepcionTurno` | usuario, tipo (`TIPO_EXCEPCION`: vacaciones, permiso, horario especial), desde, hasta | ModeloBase |
| `Feriado` | fecha, nombre, equipo (nulo = todos) | ModeloBase |
| `Portal` | nombre, slug, logo, color_principal, telefono_atencion, idiomas, sitios_autorizados, enlace_privado, activo | ModeloBase |
| `Producto` | portal, padre (FK a sí mismo, opcional, un solo nivel), slug, nombre/descripcion en es-en-pt, duracion, antelacion, margen, limite_dia, limite_semana, ventana_dias (nulos = heredan del padre o de `ParametroSistema`), activo | ModeloBase |
| `ReglaAsignacion` | portal, producto, proyecto, equipo, estrategia (`ESTRATEGIA_ASIGNACION`: todo el equipo, rotación, menor carga), excepciones de tiempos | ModeloBase |
| `Cliente` | codigo, nombres, correo (único lógico), telefono, idioma, zona_horaria, portal_origen, nota_privada | ModeloBase |
| `CapturaTecnica` | cliente, ip, ciudad, pais, idioma_navegador, dispositivo, pagina_llegada, referente | ModeloBase. La IP se borra a los 90 días: por eso **no** puede ser `RegistroInmutable` |
| `Solicitud` | codigo (`REQ-…`), portal, producto, proyecto, cliente, motivo, origen (`ORIGEN_SOLICITUD`), estado (`ESTADO_SOLICITUD`: en cola, asignada, realizada, cerrada, cancelada), telefono_para_llamar | ModeloBase |
| `Cita` | codigo (`QW-…`), solicitud, cliente, equipo, organizador, inicio, fin, estado (`ESTADO_CITA`), google_event_id, enlace_meet, asignada_por (`ASIGNADA_POR`), numero_sesion, asistencia, idioma, sincronizada_google | ModeloBase |
| `ParticipanteCita` | cita, usuario, rol, respuesta (`RESPUESTA_INVITACION`) | ModeloBase |
| `CierreCita` | cita (OneToOne), resumen, pidio_proforma, fue_soporte, es_lead, asistio, tipo_reunion, origen_resumen (manual / Meet), enlace_documento | ModeloBase |
| `NotaCita` | cita, texto (autoguardado) | ModeloBase |
| `BloqueOcupado` | usuario, inicio, fin, fuente (`FUENTE_BLOQUEO`: cita, google), cita | ModeloBase + **restricción de exclusión** (§5.3) |
| `ReservaTemporal` | producto, usuario(s), inicio, fin, token_hash, vence | ModeloBase (al vencer, `status=False`) |
| `TokenAcceso` | tipo (`TIPO_TOKEN`: gestión de cita, enlace personal), token_hash, cita o cliente, vence, ultimo_uso, usos, revocado | ModeloBase |
| `ActividadCita` | cita, accion, detalle, autor | **`RegistroInmutable`** (línea de actividad: no se edita ni se borra) ✅ |
| `EnvioRecordatorio` | cita, tipo (24 h / 1 h), enviado_en, exito, detalle | **`RegistroInmutable`** con unicidad (cita, tipo) para no enviar dos veces ✅ |

Notas:
- **`RegistroInmutable` en lugar de `ModeloBase`** para `ActividadCita` y `EnvioRecordatorio`: ✅ decidido el 2026-10-08 (es evidencia; `CLAUDE.md` lo permite).
- **Alertas y parámetros** no son modelos nuevos: se reutilizan `seguridad.Notificacion` y `seguridad.ParametroSistema`.
- **`get_or_create` / `update_or_create`** sobre claves únicas (`PerfilAgenda` por usuario, `Cliente` por correo): `status` va en `defaults`, no en la búsqueda.
- **V2:** `Lead`, `SeguimientoLead`, `Proforma`, `ItemProforma`, `Contacto`, `VistaGuardada`. **V3:** `CorreoVinculado`, `CanalGoogle`.

---

## 5. Choques entre el estudio y el repo, y cómo se resuelven

| Tema | El estudio dice | El repo hoy | Propuesta |
|---|---|---|---|
| Tareas de fondo | Celery + Redis + Beat | Se quitaron a propósito | ✅ **Decidido (2026-10-08):** **TareaCron + management commands + crontab**. Las acciones de la persona (crear evento, mandar correo) van en línea o con el hilo de `core.correos`. Basta para ~7 personas. |
| Caché de disponibilidad | Redis 1–5 min | `LocMemCache` por proceso | Usar un alias `agenda` con **`DatabaseCache`** (tabla en PostgreSQL, compartido entre workers, sin Redis). La revalidación al confirmar es la que manda. |
| API | DRF + drf-spectacular | Vistas por función con `if action` + `JsonResponse` | ✅ **Decidido (2026-10-08):** **Seguir la convención del repo**: endpoints JSON como acciones GET/POST de cada vista. Sin DRF en V1 (menos dependencias, mismo patrón que el resto). |
| Horas | Guardar en UTC | `USE_TZ = False`, hora local naive | ✅ **Decidido (2026-10-08):** **Mantener `USE_TZ=False`** y guardar en hora de Ecuador: Ecuador no tiene horario de verano, así que la hora local equivale a UTC−5 fijo y no es ambigua. Se convierte a la zona del cliente (Brasil, etc.) **solo al mostrar**, con `zoneinfo`. Cambiar `USE_TZ` correría todas las fechas ya guardadas. |
| Doble asignación | Restricción de exclusión con `tstzrange` | — | `ExclusionConstraint` sobre `tsrange(inicio, fin)` + `usuario` en `BloqueOcupado`, con `BtreeGistExtension` en la migración. Requiere `django.contrib.postgres` en `INSTALLED_APPS`. |
| Ingreso | Con la cuenta de Google Workspace | Login propio | V1 con el login actual. El ingreso con Google queda como mejora (fase 7). |
| Dominios | Un portal por dominio, CORS, certificados | `ALLOWED_HOSTS` fijo, `X_FRAME_OPTIONS='SAMEORIGIN'` | ✅ **Decidido (2026-10-08): un solo dominio.** Cada portal y producto es una ruta (`dominio/<portal>/<producto>/`), así que no hace falta resolver el portal por `Host`, ni `ALLOWED_HOSTS` dinámico, ni un certificado por portal. Solo la ventana incrustada en sitios de terceros necesita eximirse de X-Frame y enviar `Content-Security-Policy: frame-ancestors <sitios autorizados del portal>`. |
| Idiomas | Django gettext en portal y correos | `USE_I18N=True`, solo español | Activar `LocaleMiddleware` y `LANGUAGES` (es, en, pt). Las rutas del portal llevan el idioma elegido; los textos de producto van en campos por idioma. El micrositio interno queda en español. |
| Proformas (V2) | WeasyPrint «ya forma parte del stack» | No está instalado | Se decide en V2 (WeasyPrint o reportlab). |
| Python | Recomienda 3.12 + Django 5.2 | 3.11 + Django 5.2.17 LTS | Ya cumple Django 5.2 LTS; 3.11 tiene soporte de seguridad hasta 2027. |

---

## 5b. Avance (2026-10-08)

- ✅ Fase 0/1: app `agenda` creada y registrada; modelos `Proyecto`, `Equipo`, `MiembroEquipo`, `PatronTurno`, `FranjaTurno`, `ExcepcionTurno`, `Feriado` (sin tabla «Persona»: la agenda usa `Usuario` directo, decisión del usuario). Pantallas Mis turnos, Proyectos, Equipos, Feriados; feriados de Ecuador 2026–2030 cargados (`scripts/seed_feriados_ecuador.py`, API Nager.Date + traslados de ley); parámetros globales (`scripts/seed_parametros_agenda.py`).
- ✅ Roles: grupos Líder general / Líder de equipo / Coordinador / Miembro (`scripts/seed_roles_agenda.py`) y alcance por rol en vistas (`agenda/funciones_permisos.py`).
- ✅ Conexión Google Calendar por usuario (OAuth, token cifrado) en «Mis aplicaciones» (`agenda/funciones_google.py`, `view_aplicaciones.py`), multiproveedor (Teams y Zoom reservados). Claves `GOOGLE_OAUTH_*` en `credenciales.json`; pasos de Google Cloud en `README.md`.
- ✅ Adelantado de fase 3: `Portal` y `Producto` + portal de ejemplo (`scripts/seed_portal_ejemplo.py`).
- ✅ Landing pública en `/` (`public/view_landing.py`, `templates/public/landing.html`): estilo plano (Geist, blanco), hero con foto de fondo configurable desde Configuración → Identidad gráfica (`Configuracion.fondo_landing`) y velo azul sólido; botón «Agendar cita» por producto → `/agendar/<producto>/` (sin slug de portal; un solo dominio). Login (`templates/public/seguridad/base_auth.html`, `static/css/public/auth.css`, `static/js/public/auth.js`) alineado con la landing: logo enlazado a `/`.
- ✅ Fase 2 (motor): `agenda/funciones_disponibilidad.py` (ocupación por turnos + citas + Google freebusy con cache, espacios libres y comunes), `agenda/funciones_citas.py` (crear/mover/cancelar/cerrar con `select_for_update` y sincronización Google en `on_commit`), modelos de citas en `agenda/models_citas.py` con `ExclusionConstraint` (`tstzrange`) que impide doble asignación en base.
- ✅ Fase 5 (parcial): Mi día (`/agenda/mi-dia/`), Mi agenda con FullCalendar (`/agenda/mi-agenda/`, mover citas), Citas (`/agenda/citas/`, detalle `/agenda/citas/<pk>/` con notas, cierre, reprogramar, cancelar, resincronizar), Agenda del equipo (`/agenda/agenda-equipo/`: un carril por persona, espacios comunes y agendar desde la celda).
- ✅ Fase 4 (portal público, en `public/view_portal.py` + `agenda/funciones_portal.py` + `agenda/funciones_tokens.py`): `/agendar/<producto>/` en 3 pasos (día con fechas destacadas + «ver más», hora, datos) con «pedir que me llamen» → cola; `Cliente` automático; `Cita` con invitación y Meet vía el organizador; `TokenAcceso` (solo hash, vence, cuenta usos) para `/cita/<token>/` (confirmación con QR, cambiar fecha, cancelar) y `/conectar/<portal>/<token>/` (ventana del cliente: próximas, historial, agendar otra); correo `templates/email/cita_confirmada.html`; `rate_limit` en las tres vistas; sin `log()` de admin (usuario anónimo). Pruebas en `PortalTests`.
- ✅ Fase 5 (resto): Solicitudes/Cola (`/agenda/solicitudes/`: asignar horario con primer espacio sugerido, cerrar sin cita), Portales y productos (`/agenda/portales/`: CRUD, subproductos, pausar, enlace + QR por producto), Parámetros de la agenda (`/agenda/parametros/`: tiempos, portal, cliente, recordatorios con restaurar). Mi agenda: seleccionar un espacio en el calendario abre «Nueva cita» ahí mismo (`action=agendar`).
- ✅ Fase 6 (parcial): recordatorios al cliente por cron — `python manage.py recordatorios_citas` cada 15 min (`agenda/funciones_recordatorios.py`, `EnvioRecordatorio` como guarda anti-duplicado, horas en el parámetro `recordatorio_horas_antes`), registrado en el panel de crons por `scripts/seed_crons_mantenimiento.py`.
- ✅ Clientes (`/agenda/clientes/` + ficha `/agenda/clientes/<pk>/`): historial, continuidad (quién lo atendió), nota privada con autoguardado, enlace personal, agendar desde la ficha.
- ✅ Alertas (`/agenda/alertas/`, `agenda/funciones_alertas.py`): alerta flotante en todo el panel (`static/js/agenda/alerta_flotante.js`, incluido en `base.html`; consulta `?action=pendientes` cada minuto; «Avisar en 5», «Llego tarde» → anota, avisa al equipo y manda correo al cliente), centro de alertas sobre `Notificacion`, preferencias en `PreferenciaAgenda` (minutos, pantalla, push, correo), aviso a participantes al crear cita, aviso cuando Google rechaza el token. Cron `avisos_citas` (cada 5 min) crea notificación + push.
- ✅ Primer ingreso: guía de tres pasos en Hoy (`guia` en `view_mi_dia.py`) hasta que el usuario la cierra.
- ✅ Búsqueda global (`/agenda/buscar/`, `agenda/funciones_busqueda.py`): la lupa del topbar busca clientes, citas y solicitudes con `unaccent` (migración 0008 instala `unaccent` y `pg_trgm`).
- ✅ Solicitudes en tablero (`?vista=tablero`, arrastre nativo HTML5): soltar en «Con cita» abre asignar, en «Cerradas» cierra sin cita.
- ✅ Portal: apartado temporal del horario (caché, `portal_reserva_temporal_min`, por sesión anónima), ventana incrustable `/incrustar/<portal>/` + `?ventana=1` en agendar/cita (sin cabecera ni pie, `frame-ancestors` con los `sitios_autorizados` del portal; snippet en Portales → «Incrustar»), `CapturaTecnica` (IP, navegador, origen; anonimizada por el cron `mantenimiento_agenda` pasado `cliente_conservar_ip_dias`).
- ✅ Reconciliación con Google (`agenda/funciones_reconciliacion.py`, cron `reconciliar_google` cada hora): reintenta citas sin evento, detecta eventos borrados (cita → pendiente + alerta), movidos (se mueve aquí o alerta de conflicto), refresca Meet y respuestas de invitados.
- ✅ Móvil: Calendario abre en vista «Lista» del día en pantallas chicas; el cierre y «Reprogramar» viven en el detalle de la cita.
- ✅ Rehecho sobre la maqueta (2026-10-08, tarde): shell propio del micrositio (`templates/agenda/base_agenda.html` + `static/css/agenda/micrositio.css` + `agenda/context_processors.py`: barra lateral con las 17 pantallas y contadores, fondo crema, horas en monospace); Mi agenda con rejilla propia de 40 min (día/semana/mes), chips por proyecto, fuera de turno rayado, arrastrar cita para mover, columna «Por asignar» con arrastre de la cola a un espacio (`/agenda/mi-agenda/`); Cola de solicitudes como lista + detalle con espacios sugeridos y «Asignar y enviar invitación» (`/agenda/cola/`); Mi día con KPIs a la derecha y «Nueva cita»; Portal público en 4 pasos con fechas destacadas, calendario mensual con cupos, resumen azul «Su cita», «pedir que me llamen» y selector Español/English/Português (`TextoPortal` + `scripts/seed_textos_portal.py`, respaldo en `agenda/textos_portal.py`); Portales como lista de productos + panel «Compartir» (QR, Página/Ventana/Incrustado, tiempos); Clientes como lista + ficha (continuidad, nota privada, datos captados, quién lo atendió); Configuración con Tiempos/Portal/Clientes/Recordatorios + Google Workspace + Alertas y correo + historial de cambios.
- ✅ Pruebas: `agenda/tests.py` (turnos, permisos, Google con mocks, portal, apartado, incrustar, búsqueda) — `python manage.py test agenda`.
- Pendiente (fase 7): traducciones en/pt del portal y correos (los campos `nombre_en`/`descripcion_en`/`_pt` ya existen), Teams y Zoom como proveedores (reservados en `PROVEEDOR_APLICACION`), `ReglaAsignacion` (rotación entre responsables), ingreso con Google.

## 6. Plan por fases (V1)

Cada fase termina en algo que se puede mostrar. Antes de cada fase: spec corta → `grilling` → implementar → revisión → verificación a fondo cuando corresponda (`CLAUDE.md`).

| Fase | Entregable | Pantallas de la maqueta | Verificación a fondo |
|---|---|---|---|
| **0. Preparación** | Proyecto de Google Cloud, cuenta de servicio con delegación de dominio (scopes `calendar.events` y `calendar.freebusy`), prueba de crear un evento con Meet en nombre del líder. App `agenda` creada y registrada. Grupos y módulos sembrados (`scripts/seed_modulos.py`). Parámetros sembrados (`scripts/seed_parametros_agenda.py`). | — | Credencial y delegación |
| **1. Personas, equipos y turnos** | `PerfilAgenda`, `Proyecto`, `Equipo`, `MiembroEquipo`, `PatronTurno`, `FranjaTurno`, `ExcepcionTurno`, `Feriado`. Pantallas de personas y equipos, Mis turnos (relleno rápido, copiar día, vigencia por rango, excepciones). | Mis turnos | — |
| **2. Conector Google y motor de disponibilidad** | `funciones_google.py` (freebusy, insert/patch/delete con Meet, `quotaUser`), `funciones_disponibilidad.py` (patrón vigente − excepciones − feriados − Google − citas − márgenes; antelación y ventana; caché), `BloqueOcupado` con exclusión. Pruebas de casos borde. | Vista de equipo | **Sí**: solapamientos, márgenes, límites, eventos de todo el día, tentativos |
| **3. Portales y productos (admin)** | `Portal`, `Producto` (subproductos y herencia), `ReglaAsignacion`. Marca, ruta, enlace, QR, fragmento para incrustar, aviso por color de horarios libres, controles de agenda. | Portales de reserva | — |
| **4. Portal público (en `public/`)** | Landing del portal (productos y subproductos con horarios libres), agendar en 4 pasos (3 fechas próximas + calendario del mes, hora en botones, datos, confirmación), apartado de 10 min, «pedir que me llamen» → cola, `Cliente` automático, `CapturaTecnica`, `TokenAcceso`, evento con Meet, correo de confirmación con enlace personal y QR. Mis citas (ver, cambiar, cancelar, pedir otra, historial). Ventana incrustada. Rate limit y captcha. | Portal: productos, agendar, mis citas, en ventana, en teléfono | **Sí**: tokens (hash, alcance, vigencia, revocación), doble reserva, CORS/X-Frame |
| **5. Micrositio: operación diaria** | Mi día, Mi agenda (FullCalendar: mover, alargar, arrastrar desde la cola), Cola de solicitudes (espacios sugeridos y asignar), Solicitudes (tablero con SortableJS y tabla), Página de reunión (notas con autoguardado, cierre, actividad), Clientes (ficha y continuidad), Búsqueda global (PostgreSQL full text + `unaccent` + `pg_trgm`). | Mi día, Mi agenda, Cola, Solicitudes, Página de reunión, Clientes, Búsqueda | Permisos por rol en cada acción |
| **6. Alertas y recordatorios** | Alerta en pantalla (10 min / ahora, avisar en 5, llego tarde), push con `pwa`, centro de alertas sobre `Notificacion`, preferencias, recordatorios al cliente (1 día y 1 hora) por cron, primer ingreso. | Alerta de reunión, Centro de alertas, Primer ingreso | Duplicados de envío |
| **7. Móvil, idiomas y cierre de V1** | Pantallas móviles (lista por día, «Mover a» sin arrastrar, cierre en un paso). Traducción en/pt del portal y los correos. Configuración (parámetros + historial). Reconciliación periódica con Google. Ingreso con Google (opcional). | Versiones móviles, Configuración | Reconciliación |

V2 (leads, seguimiento, proformas, reportes, resumen desde Meet, enlaces de un solo uso) y V3 (correo en el CRM) se planifican cuando cierre V1.

---

## 7. Pantallas de la maqueta → vista, plantilla y fase

| # | Pantalla de la demo | Vista | Fase |
|---|---|---|---|
| 00 | Mi día | `agenda/view_mi_dia.py` | 5 |
| 01 | Cola de solicitudes | `agenda/view_cola.py` | 5 |
| 02 | Vista de equipo | `agenda/view_equipo.py` | 2–5 |
| 04 | Mi agenda (semana) | `agenda/view_agenda.py` | 5 |
| 05 | Solicitudes, tablero y tabla | `agenda/view_solicitudes.py` | 5 |
| 06 | Búsqueda global | `agenda/view_busqueda.py` | 5 |
| 07 | Página de reunión | `agenda/view_reunion.py` | 5 |
| 08 / 14 | Alerta de reunión (web / móvil) | JS global + `agenda/view_alertas.py` | 6 |
| 09 | Centro de alertas | `agenda/view_alertas.py` | 6 |
| 10 | Mis turnos | `agenda/view_turnos.py` | 1 |
| 11 | Configuración | `agenda/view_configuracion.py` (sobre `ParametroSistema`) | 7 |
| 23 | Portales de reserva (admin) | `agenda/view_portales.py` | 3 |
| 24 | Clientes y continuidad | `agenda/view_clientes.py` | 5 |
| 03, 12, 13, 15, 16 | Móvil: Mi día, agenda, mover, cierre, cola | Las mismas vistas, plantillas responsive o variantes | 7 |
| 17 | Primer ingreso | `agenda/view_mi_dia.py` (acción) + `pwa` | 6 |
| 18, 22 | Portal: agendar (web y teléfono) | `public/portal/view_portal.py` | 4 |
| 19 | Portal: mis citas | `public/portal/view_mis_citas.py` | 4 |
| 20 | Portal: productos y subproductos (landing) | `public/portal/view_portal.py` | 4 |
| 21 | Portal en ventana sobre otro sitio | `public/portal/view_incrustar.py` | 4 |

Identidad visual:
- **Micrositio:** colores de Exducere Online, azul `#005082` como principal y verde `#67BD01` como acento, aplicados como tokens en `static/base_adicional.css`.
- **Portal:** el color y el logo de cada `Portal`, con contraste comprobado al guardar.

---

## 8. Decisiones que hay que tomar antes de la fase 0

1. ✅ **Credencial de la cuenta de servicio:** decidido el 2026-10-08 — en `credenciales.json` (por ejemplo `GOOGLE_SERVICE_ACCOUNT_FILE` con la ruta al JSON, fuera del repo, y `GOOGLE_ORGANIZADOR_DEFAULT`). La pantalla «Configuración» muestra solo el estado de la conexión, sin campo para reemplazar la credencial.
2. ✅ **`USE_TZ`:** decidido el 2026-10-08 — se mantiene `False` con hora de Ecuador (§5).
3. ✅ **Sin DRF:** decidido el 2026-10-08 — API JSON con el patrón `if action`, sin DRF.
3b. ✅ **Sin Celery/Redis:** decidido el 2026-10-08 — tareas con `TareaCron` + management commands + crontab.
4. ✅ **`RegistroInmutable`** para `ActividadCita` y `EnvioRecordatorio`: decidido el 2026-10-08.
5. ✅ **Dominios:** decidido el 2026-10-08 — un solo dominio; portales y productos como rutas.
6. Las preguntas abiertas del propio estudio: antelación «24 h + 1 día de holgura», CC ocupado, «llego tarde» por correo o push, teléfono de atención, quién revisa las traducciones y nombre del producto.

---

## 9. Riesgos técnicos a verificar pronto

- **FullCalendar:** la del repo es la **v3.10.1** (`static/assets/plugins/fullcalendar`), con jQuery. El estudio asume la v6 estándar (MIT) con elementos externos. Para la fase 5 hay que traer la v6 (sin jQuery) y verificar en una prueba corta que arrastrar desde la cola funciona en la edición estándar.
- **Delegación de dominio:** con la cuenta de servicio, cada llamada se hace en nombre de un usuario (`subject`). Freebusy de varias personas en una llamada exige que ese usuario pueda ver la disponibilidad de los demás. Verificar con el administrador de Workspace.
- **GeoLite2:** la licencia exige registro en MaxMind y actualizar la base.
- **Personas mayores:** el propio estudio recomienda probar el portal con 5 clientes reales antes de construir (meta: agendar sin ayuda en menos de 2 minutos).

---

## 10. Datos de ejemplo para las ventanas de producto

Fuente: `docs/productos_para_publico`. Se cargan con un seeder idempotente (`scripts/seed_portal_ejemplo.py`) en la fase 3, para que cada ventana del portal (landing de productos, agendar, Mis citas y ventana incrustada) se vea con datos reales desde el primer día.

| Producto | Subproductos | Sitio del producto (para «Ver producto» y prueba de incrustación) | Slug propuesto |
|---|---|---|---|
| Kawana Proctoring | — | https://kawana.app | `kawana` |
| Moodle con IA | — | https://moodle-assistant-demo.exducereonline.com | `moodle-ia` |
| Moodle | Web · Teléfono móvil | https://exducereonline.com | `moodle`, `moodle/web`, `moodle/movil` |
| Servidores | — | https://exducereonline.com | `servidores` |

- **Portal de ejemplo:** «Exducere Online», con los colores de la marca (`#005082` / `#67BD01`). Los sitios autorizados para la ventana incrustada son los tres dominios de la lista.
- **Nombres:** el estudio y la maqueta dicen «Qwana» y «MoAI». Los datos que dejaste dicen **«Kawana Proctoring»** y **«Moodle con IA»**. El seeder usa los nombres de la lista; hay que confirmar cuál es el definitivo.
- **Subproductos:** Moodle tiene «Web» y «Teléfono móvil», igual que en el estudio.
- **«Servidores»** es un producto nuevo que no está en el estudio. Por defecto se agenda directo, sin subproductos.
- **Textos en en/pt:** los nombres y descripciones van en los tres idiomas. Si falta uno, se muestra el español, como define el estudio.
