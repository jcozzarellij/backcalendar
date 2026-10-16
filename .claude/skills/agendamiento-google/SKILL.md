---
name: agendamiento-google
description: Usar al construir el agendamiento de citas de backcalendar con Google Calendar y Gmail — disponibilidad (freebusy), crear/mover/cancelar eventos con Meet, invitaciones y confirmaciones por correo, OAuth y guardado de tokens, sincronización por webhooks. No usar para operar el calendario personal del usuario desde el chat (para eso están los conectores de Google Calendar/Gmail).
---

# Agendamiento con Google Calendar y Gmail (backcalendar)

Las reglas del repo (`CLAUDE.md`: `ModeloBase`, patrón `if action`, soft delete, choices a nivel de módulo, copy en español) mandan sobre esta skill. Esta skill cubre **cómo** integrar Google.

## Antes de codificar: decisiones que se preguntan (skill `grilling`)

1. **Calendario de quién**: ¿un calendario central del negocio (cuenta de servicio o una cuenta OAuth fija) o el calendario de cada profesional (OAuth por usuario)?
2. **Quién agenda**: ¿el staff desde el panel, o el cliente final desde una página pública?
3. **Reglas de agenda**: duración por servicio, horario laboral, márgenes entre citas, anticipación mínima y máxima, cupo por franja.
4. **Videollamada**: ¿cada cita lleva enlace de Google Meet?
5. **Correo**: ¿la invitación de Google basta (`sendUpdates='all'`) o se manda además una confirmación propia (Gmail API o el SMTP de `core/correos.py`)?
6. **Fuente de verdad**: la BD de backcalendar es la fuente de verdad de la cita; Google es el reflejo. Si alguien edita el evento en Google, ¿se acepta el cambio o se revierte?

## Librerías

`google-api-python-client`, `google-auth`, `google-auth-oauthlib`. Agregarlas a `requirements.txt` con versión fija solo cuando se implemente.

## Credenciales

- El `client_id` y el `client_secret` de OAuth, o la ruta al JSON de la cuenta de servicio, van en `credenciales.json` con claves nuevas (por ejemplo `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`). Se reflejan en `credenciales_template.json` con valor vacío. Nunca se leen ni se escriben valores reales de `credenciales.json`.
- El refresh token por usuario va en BD **cifrado** con `core/crypto.py`, en un modelo `ModeloBase` (por ejemplo `CuentaGoogle`: `usuario` OneToOne, `email`, `refresh_token_cifrado`, `scopes`, `calendario_id`, `activo`). En `update_or_create` por `usuario`, `status` va en `defaults`, no en la búsqueda.
- Scopes mínimos: `https://www.googleapis.com/auth/calendar.events` para eventos, `https://www.googleapis.com/auth/calendar.freebusy` para la disponibilidad y `https://www.googleapis.com/auth/gmail.send` solo si se envía correo por Gmail. No pedir `calendar` completo ni `gmail.readonly` sin necesidad.
- Flujo OAuth web: `google_auth_oauthlib.flow.Flow.from_client_config(...)` con `access_type='offline'` y `prompt='consent'`, para que Google devuelva refresh token. El `state` se guarda en la sesión y se valida en el callback.

## Modelo de cita (orientativo)

```python
ESTADO_CITA = (
    ('pendiente', 'Pendiente'),
    ('confirmada', 'Confirmada'),
    ('cancelada', 'Cancelada'),
    ('atendida', 'Atendida'),
    ('no_asistio', 'No asistió'),
)


class Cita(ModeloBase):
    profesional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='citas')
    cliente_nombre = models.CharField(max_length=200)
    cliente_email = models.EmailField()
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CITA, default='pendiente')
    google_event_id = models.CharField(max_length=255, blank=True, default='')
    google_calendar_id = models.CharField(max_length=255, blank=True, default='')
    enlace_meet = models.URLField(blank=True, default='')
```

- `USE_TZ = False` y `TIME_ZONE = 'America/Guayaquil'`: las fechas son naive en hora local. Al hablar con Google se manda `dateTime` en ISO **con** `timeZone: 'America/Guayaquil'`, y lo que devuelve Google se convierte a hora local naive antes de guardar.
- Cancelar es cambiar `estado='cancelada'`, no hacer soft delete. El soft delete (`status=False`) es para registros cargados por error.
- La lógica de dominio (calcular franjas, chocar contra freebusy, crear/mover el evento) va en `<app>/funciones_agenda.py`. Las vistas solo despachan por `action`.

## Disponibilidad

1. Generar las franjas candidatas desde el horario laboral y la duración del servicio.
2. Restar las citas propias activas (`status=True`, estado distinto de `cancelada`).
3. Restar lo ocupado en Google con `service.freebusy().query(body={'timeMin', 'timeMax', 'timeZone': 'America/Guayaquil', 'items': [{'id': calendario_id}]})`. Consultar el rango completo de una sola vez, no franja por franja.
4. Al confirmar, revalidar dentro de `transaction.atomic()` con `select_for_update()` sobre las citas del profesional en esa franja (`ATOMIC_REQUESTS` está apagado): dos clientes no deben quedarse con la misma franja.

## Eventos

```python
evento = {
    'summary': f'Cita: {cita.cliente_nombre}',
    'start': {'dateTime': cita.inicio.isoformat(), 'timeZone': 'America/Guayaquil'},
    'end': {'dateTime': cita.fin.isoformat(), 'timeZone': 'America/Guayaquil'},
    'attendees': [{'email': cita.cliente_email}],
    'conferenceData': {'createRequest': {'requestId': f'cita-{cita.pk}', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}},
}
creado = service.events().insert(calendarId=calendario_id, body=evento,
                                  conferenceDataVersion=1, sendUpdates='all').execute()
```

- Mover la cita: `events().patch(...)` con el nuevo `start`/`end` y `sendUpdates='all'`. Cancelarla: `events().delete(..., sendUpdates='all')`, o un `patch` con `status: 'cancelled'`.
- **Idempotencia**: el `requestId` de Meet y el `google_event_id` guardado evitan duplicados si se reintenta. Si ya hay `google_event_id`, se usa `patch`, no `insert`.
- Si Google falla, la cita queda en BD y el error se registra con `log(...)`. No hay que perder la cita por un fallo externo: se reintenta luego con un cron (`seguridad.TareaCron` + management command).

## Correo

- La invitación nativa de Google (`sendUpdates='all'`) ya avisa al invitado.
- Para una confirmación con la marca propia, usar `core/correos.py` → `despachar(...)`, con plantilla en `templates/email/`. Gmail API (`users().messages().send(userId='me', body={'raw': base64url(MIME)})`) solo si el correo debe salir desde la cuenta Gmail del profesional.

## Sincronización (opcional)

`events().watch(...)` registra un canal de push: Google llama a un endpoint HTTPS público con `X-Goog-Channel-ID` y `X-Goog-Resource-State`. El endpoint no confía en el cuerpo; usa `syncToken` (`events().list(syncToken=...)`) para traer los cambios. Los canales vencen y se renuevan con un cron. En desarrollo basta un cron que haga `events().list(updatedMin=...)`.

## Errores comunes

- Pedir el refresh token sin `prompt='consent'`: Google no lo devuelve en el segundo login.
- Mandar `dateTime` naive sin `timeZone`: Google lo interpreta en UTC y la cita sale corrida 5 horas.
- Olvidar `conferenceDataVersion=1`: el enlace de Meet no se crea.
- Calcular la disponibilidad solo con Google o solo con la BD: hay que restar ambas.
