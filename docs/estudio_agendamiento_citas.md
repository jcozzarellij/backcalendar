# Estudio — Agendamiento de citas estilo Prelude en backcalendar

Fecha: 2026-10-08 · Estado: estudio (sin implementar)

Decisiones ya tomadas por el usuario:
- **Calendario de cada profesional**: cada profesional conecta su propio Google Calendar por OAuth.
- **El cliente reserva desde una página pública**, sin cuenta en la plataforma.

Base: el estudio de Prelude en `.ai/docs/estudio_prelude_2026-10-08.md` y la skill `agendamiento-google`.

---

## 1. Qué tomamos de Prelude

Prelude agenda entrevistas: candidato ↔ entrevistadores, sobre los calendarios reales. Lo que se traslada a citas:

| Prelude | backcalendar |
|---|---|
| Enlace de autoagendamiento del candidato | Página pública de reserva por servicio y por profesional |
| Disponibilidad cruzada con el calendario real | Horario laboral − citas propias − `freebusy` de Google del profesional |
| Pool de entrevistadores + balanceo de carga | "Cualquier profesional disponible" con rotación y tope diario/semanal |
| Invitaciones y recordatorios por correo y SMS | Invitación de Google + confirmación propia + recordatorios por correo (WhatsApp, fase 3) |
| Reprogramar a todas las partes sin empezar de cero | Enlace firmado en el correo para reprogramar o cancelar |
| Paneles (varios entrevistadores) | Fase 3: cita con varios profesionales |
| Analítica de carga y reprogramaciones | Métricas de ocupación, cancelaciones e inasistencias |
| Shadowing, integración con ATS | No aplica |

---

## 2. Actores y flujos

### 2.1 Profesional (staff, `Usuario.is_staff`)
1. Entra al panel, va a **Mi agenda** y luego a **Conectar Google Calendar** (OAuth).
2. Define su **horario laboral** por día, sus **bloqueos** (vacaciones, almuerzo) y los **servicios** que presta.
3. Ve sus citas del día y de la semana, marca **atendida** o **no asistió** y puede cancelar o reprogramar.

### 2.2 Administrador
- CRUD de **servicios** y alta de **profesionales**.
- Ve todas las agendas, reasigna citas y consulta las métricas.

### 2.3 Cliente (público, sin cuenta)
1. Abre `/reservar/` o `/reservar/<slug-servicio>/` o `/reservar/p/<slug-profesional>/`.
2. Elige el **servicio**, luego el **profesional** (o "cualquiera disponible"), luego el **día** (calendario con días que tienen cupo) y la **franja horaria**.
3. Llena sus datos (nombres, correo, teléfono) y las preguntas previas del servicio, si las hay.
4. Confirma. Recibe la **invitación de Google** (con Meet si es virtual) y un **correo de confirmación** propio con los enlaces "Reprogramar" y "Cancelar".
5. Recibe **recordatorios** 24 h y 1 h antes.

---

## 3. Integración con Google (calendario por profesional)

### 3.1 OAuth por profesional
- Flujo web con `google-auth-oauthlib`: `Flow.from_client_config(...)`, `access_type='offline'`, `prompt='consent'` (sin `prompt='consent'` Google no repite el refresh token) e `include_granted_scopes='true'`.
- El `state` se guarda en la sesión y se valida en el callback (CSRF del flujo OAuth).
- El **refresh token** se guarda **cifrado** con `core/crypto.py` (`EncryptedTextField` / `encrypt_text`), nunca en texto plano ni en logs. `core/log_filters.py` ya enmascara Bearer en los logs.
- Al desconectar, revocar en `https://oauth2.googleapis.com/revoke`, poner `activo=False` y vaciar el token.
- Si Google responde `invalid_grant` (token vencido o revocado): marcar la cuenta como desconectada, avisar al profesional (notificación + correo) y sacarlo de la reserva pública hasta que reconecte.

### 3.2 Scopes mínimos
| Scope | Para qué |
|---|---|
| `https://www.googleapis.com/auth/calendar.events` | Crear, mover y cancelar los eventos de las citas |
| `https://www.googleapis.com/auth/calendar.freebusy` | Leer solo ocupado/libre, sin ver el detalle de los eventos personales |
| `openid email` | Saber qué cuenta conectó |

No pedir `calendar` completo. **Gmail API no es necesaria**: la invitación la manda Google Calendar y la confirmación sale por el SMTP del proyecto (`core/correos.py`). Si en el futuro el correo debe salir desde el Gmail del profesional, se agrega `gmail.send`, con una verificación más exigente.

### 3.3 Requisito importante: verificación de la app de Google
- Con el proyecto de Google Cloud en estado **"Testing"** (tipo de usuario externo), los refresh tokens **vencen a los 7 días** y solo entran usuarios de prueba. En producción hay que **publicar la app y pasar la verificación de Google**; los scopes de Calendar son sensibles y la revisión pide dominio verificado, política de privacidad y una demostración del uso.
- Si todos los profesionales están en un **Google Workspace propio**, se puede usar el tipo de usuario **"Interno"**: sin verificación y sin el vencimiento de 7 días.
- **Esto se decide antes de desarrollar**: cambia los plazos del proyecto.

### 3.4 Disponibilidad
Algoritmo por profesional y por día:
1. Franjas candidatas = `HorarioLaboral` del día, partido en pasos (por ejemplo cada 15 min) del largo del servicio.
2. Quitar los `BloqueoAgenda`.
3. Quitar las `Cita` activas (`status=True`, estado distinto de `cancelada`), cada una ensanchada por el margen antes y después del servicio.
4. Quitar lo ocupado en Google: `freebusy.query` con `timeMin`/`timeMax` del rango pedido y `timeZone='America/Guayaquil'`. **Una llamada por profesional y por rango** (cada profesional tiene su propio token), nunca una llamada por franja.
5. Aplicar la anticipación mínima y máxima del servicio y los topes diario/semanal.

- **Cache**: guardar el `freebusy` de cada profesional en cache 2–5 minutos por rango (el `LocMemCache` actual es por proceso: sirve en desarrollo; con varios workers en producción cada uno tiene su copia, lo cual se acepta porque la revalidación al confirmar es la que manda).
- **"Cualquier profesional"**: se calcula la unión de franjas de todos los que prestan el servicio. Al confirmar se elige entre los libres según la regla de **rotación** (el que tenga menos citas en la semana y, si empatan, el que lleva más tiempo sin cita).
- Límites conocidos de `freebusy`: hasta 50 calendarios por consulta. Como aquí cada profesional usa su propio token, eso no aplica.

### 3.5 Confirmar sin doble reserva
`ATOMIC_REQUESTS=False` en backcalendar, así que el bloqueo va explícito:
```
with transaction.atomic():
    Profesional.objects.select_for_update().get(pk=...)    # serializa reservas del mismo profesional
    revalidar que la franja siga libre (BD)                # sin esto, dos clientes pueden tomarla
    crear Cita(estado='confirmada')
fuera de la transacción: crear evento en Google
```
- La llamada a Google va **después** del commit: una API lenta no debe tener una transacción abierta.
- Si Google falla, la cita existe igual y queda `sincronizada_google=False`. Un cron la reintenta y el profesional ve una alerta.
- Se revalida también contra `freebusy` justo antes de confirmar, por si el profesional llenó ese hueco en Google mientras el cliente llenaba el formulario.

### 3.6 Evento en Google
- `events.insert(calendarId='primary', conferenceDataVersion=1, sendUpdates='all')`, con `start` y `end` en ISO **más** `timeZone`, `attendees=[cliente]` y `conferenceData.createRequest.requestId=f'cita-{pk}'` (idempotente) si es virtual.
- `extendedProperties.private = {'cita_id': pk}` sirve para reconocer el evento como propio al sincronizar.
- Reprogramar: `events.patch` con el nuevo horario. Cancelar: `events.delete(sendUpdates='all')`.
- Fechas: el proyecto usa `USE_TZ=False` con hora local naive de Guayaquil. Hacia Google siempre se manda `timeZone`; desde Google se convierte a local naive antes de guardar.

### 3.7 Si el profesional mueve o borra el evento en Google (fase 3)
Se registra `events.watch` por profesional hacia un endpoint HTTPS público. El aviso de Google no trae datos: con `syncToken` se piden los cambios. Si un evento con `cita_id` se movió o se borró, se actualiza la cita y se avisa al cliente. Los canales vencen y los renueva un cron. Hasta tener esto, la regla es: **la cita se gestiona desde backcalendar, no desde Google**.

---

## 4. Modelos (borrador — todos `ModeloBase`, choices a nivel de módulo, nueva app `agenda`)

```
MODALIDAD_SERVICIO = (('presencial', 'Presencial'), ('virtual', 'Virtual'))
DIA_SEMANA = ((0, 'Lunes'), …, (6, 'Domingo'))
ESTADO_CITA = (('confirmada', 'Confirmada'), ('cancelada', 'Cancelada'),
               ('atendida', 'Atendida'), ('no_asistio', 'No asistió'))
ORIGEN_CITA = (('publica', 'Página pública'), ('panel', 'Panel'))
```

| Modelo | Campos principales | Notas |
|---|---|---|
| `Servicio` | nombre, slug, descripcion, duracion_min, margen_antes_min, margen_despues_min, modalidad, anticipacion_min_horas, anticipacion_max_dias, color, activo | `slug` único → URL pública |
| `Profesional` | usuario (OneToOne `Usuario`), slug, titulo, foto, tope_diario, tope_semanal, publico (bool), activo | Perfil de agenda del staff |
| `ProfesionalServicio` | profesional, servicio, activo | Quién presta qué |
| `HorarioLaboral` | profesional, dia_semana, hora_inicio, hora_fin | Varias franjas por día |
| `BloqueoAgenda` | profesional, inicio, fin, motivo | Vacaciones, feriados |
| `CuentaGoogle` | profesional (OneToOne), email, refresh_token (`EncryptedTextField`), scopes, conectada (bool), ultimo_error | `update_or_create` por profesional con `status` en `defaults` |
| `Cliente` | nombres, apellidos, email, telefono, documento (opcional) | Se reutiliza por email |
| `Cita` | servicio, profesional, cliente, inicio, fin, estado, origen, motivo_cancelacion, google_event_id, enlace_meet, sincronizada_google, token_gestion | `token_gestion` para los enlaces del correo |
| `PreguntaServicio` / `RespuestaCita` | servicio, texto, obligatoria / cita, pregunta, respuesta | Fase 2 |
| `EnvioRecordatorio` | cita, tipo (24h/1h), enviado_en, exito, detalle | **Registro append-only** (excepción a `ModeloBase`: hay que pedirla explícitamente según `CLAUDE.md`), o `ModeloBase` con unicidad (cita, tipo) para no enviar dos veces |

Índices: `Cita(profesional, inicio)` y `Cita(estado, inicio)` para la disponibilidad y los recordatorios.

---

## 5. Pantallas

**Panel (autenticado, `templates/agenda/...`, patrón `if action`, Bootstrap 5):**
- **Mi agenda**: vista día y semana (FullCalendar ya está en `static/assets/plugins/fullcalendar`), próximas citas y estado de la conexión con Google.
- **Horario y bloqueos** del profesional.
- **Servicios** (administrador): CRUD.
- **Profesionales** (administrador): alta desde `Usuario`, servicios, topes y visibilidad pública.
- **Citas**: listado con filtros (fecha, profesional, servicio, estado) y acciones: reprogramar, cancelar, atendida, no asistió.
- **Métricas** (fase 2): ocupación por profesional, cancelaciones, inasistencias, horarios más pedidos.

**Público (`public/` o la app `agenda` con layout `public/base.html`):**
- `/reservar/`: servicios, luego profesional, luego calendario de días con cupo, luego franjas, luego datos, luego confirmación.
- `/cita/<token>/`: ver la cita, **reprogramar** (mismo selector de franjas) o **cancelar** (con motivo).
- Diseño mobile-first: la mayoría reservará desde el celular.

---

## 6. Correos y recordatorios

| Momento | Canal | Contenido |
|---|---|---|
| Al reservar | Invitación de Google (`sendUpdates='all'`) | Evento en el calendario del cliente, con Meet |
| Al reservar | `core/correos.py` → plantilla `templates/email/cita_confirmada.html` | Datos de la cita + enlaces Reprogramar/Cancelar |
| 24 h y 1 h antes | Cron (`TareaCron` + management command `enviar_recordatorios`) | Recordatorio con los mismos enlaces |
| Al reprogramar o cancelar | Google + correo propio | Aviso al cliente y al profesional |
| Token de Google caído | `notificacion(...)` + correo al profesional | "Reconecta tu Google Calendar" |

El cron corre cada 5–10 minutos. Busca las citas `confirmada` cuyo `inicio` cae en la ventana y que no tienen `EnvioRecordatorio` de ese tipo, y envía. La unicidad (cita, tipo) evita duplicados aunque el cron se solape.

---

## 7. Seguridad de la página pública

- **Rate limit** con `core.funciones.rate_limit` (ya existe) en consultar disponibilidad y en confirmar.
- **Anti-bots**: un campo honeypot como mínimo; captcha (Turnstile o reCAPTCHA) si aparece abuso.
- **`token_gestion`**: aleatorio largo (`secrets.token_urlsafe(32)`), nunca el `pk`. Los enlaces de gestión no revelan datos de otras citas.
- **Privacidad**: la página pública muestra solo franjas libres, nunca el detalle de los eventos de Google (por eso el scope `freebusy`).
- **CSRF**: los formularios públicos llevan token CSRF. Los endpoints JSON de disponibilidad son GET de solo lectura.
- **Validación en servidor** de todo (servicio activo, profesional público, anticipación, topes): nunca confiar en lo que mande el navegador.
- Actualizar `/proteccion-datos/` con el tratamiento de datos de clientes y de Google Calendar. La verificación de Google exige política de privacidad.

---

## 8. Dependencias y configuración

- `requirements.txt`: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, con versión fija al implementar.
- `credenciales_template.json`: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.
- Google Cloud Console: proyecto, Calendar API habilitada, pantalla de consentimiento, URI de redirección del dominio de producción.
- Lo que ya existe y se reutiliza: `core/crypto.py`, `core/correos.py`, `core/funciones.rate_limit`, `seguridad.TareaCron` + `seguridad/funciones_cron.ejecutar_cron`, `notificacion(...)`, FullCalendar en `static/assets/plugins/fullcalendar`, `public/base.html`.

---

## 9. Plan por fases

| Fase | Entregable | Depende de |
|---|---|---|
| 0 | Proyecto de Google Cloud + decisión Interno/Externo + verificación iniciada | Decisión 3.3 |
| 1 | App `agenda`: modelos, servicios, profesionales, horario, bloqueos (panel) | — |
| 2 | Conexión Google por profesional (OAuth, cifrado, desconectar, `invalid_grant`) | 0, 1 |
| 3 | Motor de disponibilidad (BD + freebusy + cache) y pruebas de casos borde | 2 |
| 4 | Página pública de reserva + confirmación sin doble reserva + evento en Google + correo | 3 |
| 5 | Gestión por token (reprogramar/cancelar) + recordatorios por cron | 4 |
| 6 | "Cualquier profesional" con rotación y topes + métricas + preguntas previas | 5 |
| 7 | Sincronización inversa por webhooks, WhatsApp, citas con varios profesionales | 6 |

Casos borde a probar en la fase 3: franja que cruza el fin del horario, margen que invade la siguiente cita, día con bloqueo parcial, evento de Google de todo el día, cita en el límite de la anticipación mínima, dos reservas simultáneas de la misma franja, profesional con el token revocado a mitad de la reserva.

---

## 10. Preguntas abiertas

1. ¿Los profesionales tienen Google Workspace del negocio (app **Interna**, sin verificación) o Gmail personales (app **Externa**, con verificación de Google)?
2. ¿Rubro y servicios concretos? (duraciones, si hay presencial y virtual, si hay salas o recursos físicos).
3. ¿Pago o seña al reservar?
4. ¿Recordatorios solo por correo, o también WhatsApp?
5. ¿Una sede o varias?
6. ¿Puede el cliente elegir al profesional, o siempre "cualquiera"?
7. ¿Política de cancelación (por ejemplo, no cancelar con menos de X horas)?

---

## Fuentes

- Prelude — SelectSoftwareReviews: https://www.selectsoftwarereviews.com/reviews/interview-scheduling-prelude
- Prelude — GetApp: https://www.getapp.co.uk/software/2050573/prelude
- Alternativa Cronofy: https://www.cronofy.com/api/markdown/prelude-alternative
- Refresh token de 7 días en modo Testing: https://www.unipile.com/google-oauth-refresh-token/
- Límites de freebusy: https://cli.nylas.com/guides/google-calendar-api-free-busy
- Referencia freebusy v3: https://developers.google.com/resources/api-libraries/documentation/calendar/v3/php/latest/class-Google_Service_Calendar_Freebusy_Resource.html
