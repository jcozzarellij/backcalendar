---
tags: [estudio, agendamiento, prelude]
estado: backlog
actualizado: 2026-10-08
resumen: Estudio de Prelude (agendamiento de entrevistas) y cómo trasladar sus ideas a un agendamiento de citas en backcalendar con Google Calendar y Gmail. Sin implementar.
---

# Estudio: Prelude → agendamiento de citas en backcalendar

## 1. Qué es Prelude

Prelude (prelude.co, antes "Interview Schedule") es una plataforma de **agendamiento de entrevistas** para equipos de reclutamiento. Su promesa es quitar el ida y vuelta de correos para coordinar a un candidato con varios entrevistadores. Glassdoor reporta haber bajado el tiempo de agendar una entrevista de 4–5 horas a unos 11,5 minutos.

Se apoya en el calendario real de cada persona (Google Workspace u Office 365), en la herramienta de videollamada (Meet, Zoom o Teams) y en el sistema de reclutamiento (Greenhouse, Lever, Workday).

Fuentes: SelectSoftwareReviews, GetApp, Software Advice y la comparativa de Cronofy (ver §8).

## 2. Funciones de Prelude

| Área | Qué hace |
|---|---|
| **Autoagendamiento** | El candidato recibe un enlace y elige una franja dentro de una ventana definida. Al reservar, a todos les llegan las invitaciones de calendario. |
| **Disponibilidad** | Cada entrevistador gestiona sus preferencias y su disponibilidad; el sistema cruza los calendarios reales. También busca a la vez varias ventanas de disponibilidad del candidato. |
| **Paneles** | Una cita con varios entrevistadores: duración, hora de inicio y orden de cada tramo. Los paneles se guardan como plantillas reutilizables. |
| **Pools y atributos** | Los entrevistadores llevan atributos (habilidad, idioma, nivel). El panel se arma filtrando por atributo y repartiendo la carga. |
| **Balanceo de carga** | Tope diario y semanal de entrevistas por persona, con alerta al acercarse al límite. Rotación entre los del pool. |
| **Formación** | Shadowing y reverse shadowing: un entrevistador nuevo acompaña a uno experimentado, y eso se agenda junto con la entrevista. |
| **Conflictos** | Maneja reuniones que chocan y permite reservar sobre calendarios ocupados cuando es intencional. |
| **Reprogramación** | Atiende pedidos de cambio y reprograma a todas las partes a la vez, sin empezar de cero. |
| **Comunicación** | Invitaciones y recordatorios por correo y SMS, con texto de marca, zona horaria visible para el candidato y preguntas previas opcionales. Plantillas de confirmación. |
| **Portal del candidato** | Recorrido personalizable con la marca de la empresa: ve sus citas, la hora local y los enlaces. |
| **Analítica** | Volumen de agendamientos, carga por entrevistador, reprogramaciones y rechazos, y planificación de capacidad. |
| **Planes** | Starter (agendamiento base), Growth (reportes) y Enterprise (formación, balanceo de carga e integraciones a medida). Precio solo con demo. |

## 3. Traducción al dominio de citas

| Prelude | backcalendar (citas) |
|---|---|
| Candidato | **Cliente** (persona que reserva; no necesita cuenta) |
| Entrevistador | **Profesional** (`Usuario` con `is_staff`) |
| Tipo de entrevista | **Servicio** (duración, margen, modalidad presencial o virtual) |
| Panel | **Cita con varios profesionales** o **cita en tramos** (opcional, fase 3) |
| Pool con atributos | **Profesionales que prestan un servicio** + etiquetas |
| Enlace de autoagendamiento | **Página pública de reserva** por servicio o por profesional |
| Balanceo de carga | **Tope de citas diario/semanal** por profesional y asignación rotativa |
| Shadowing | No aplica en principio. Equivalente posible: un acompañante opcional en la cita |
| ATS (Greenhouse/Lever) | No aplica. La BD de backcalendar es la fuente de verdad |

## 4. Qué conviene imitar (por fases)

**Fase 1 — núcleo (MVP)**
1. Catálogo de **servicios**: duración, margen antes y después, modalidad, anticipación mínima y máxima.
2. **Horario laboral** por profesional, con franjas por día de la semana, y **bloqueos** (vacaciones, feriados).
3. **Disponibilidad real**: franjas del horario, menos las citas propias, menos lo ocupado en Google (`freebusy`).
4. **Reserva desde el panel** (staff) y **página pública** de autoagendamiento con enlace por servicio o profesional.
5. **Evento en Google Calendar** con Meet si es virtual, invitación al cliente (`sendUpdates='all'`) y **correo de confirmación** propio.
6. **Cancelar y reprogramar** desde el panel y desde un enlace firmado del correo, sin que el cliente necesite cuenta.
7. **Recordatorios** por correo (por ejemplo 24 h y 1 h antes) con un cron (`TareaCron`).

**Fase 2 — operación**
8. **Asignación automática**: "cualquier profesional disponible" con rotación y tope diario/semanal (el balanceo de carga de Prelude).
9. **Preguntas previas** por servicio (formulario corto al reservar).
10. **Estados de la cita**: pendiente, confirmada, atendida, no asistió y cancelada, con el motivo.
11. **Panel de métricas**: citas por día, ocupación por profesional, cancelaciones y reprogramaciones, inasistencias.

**Fase 3 — avanzado**
12. Citas con **varios profesionales** o **en tramos** (los paneles de Prelude) y **plantillas** reutilizables.
13. **Sincronización inversa** por webhooks de Google (si alguien mueve el evento en Google).
14. **WhatsApp o SMS** para recordatorios (Prelude lo hace por SMS).
15. **Portal del cliente** con sus citas pasadas y futuras.

## 5. Modelos propuestos (borrador, todos `ModeloBase`, choices a nivel de módulo)

- `Servicio` — nombre, descripción, duración (min), margen_antes, margen_despues, modalidad (`MODALIDAD_SERVICIO`), anticipacion_min_horas, anticipacion_max_dias, activo, color.
- `ProfesionalServicio` — profesional (FK `Usuario`), servicio, activo (quién presta qué).
- `Profesional` (perfil) — usuario OneToOne, tope_diario, tope_semanal, zona horaria, slug público, activo.
- `HorarioLaboral` — profesional, dia_semana (`DIA_SEMANA`), hora_inicio, hora_fin.
- `BloqueoAgenda` — profesional, inicio, fin, motivo.
- `CuentaGoogle` — usuario OneToOne, email, refresh_token_cifrado (`core/crypto.py`), calendario_id, activo.
- `Cliente` — nombres, correo, teléfono, documento (opcional).
- `Cita` — servicio, profesional, cliente, inicio, fin, estado (`ESTADO_CITA`), motivo_cancelacion, google_event_id, enlace_meet, token público para cancelar o reprogramar, origen (panel o pública).
- `PreguntaServicio` / `RespuestaCita` — fase 2.
- `RecordatorioCita` — cita, tipo, programado_para, enviado_en (registro de envíos; candidato a log append-only).

## 6. Pantallas propuestas

- **Panel**: agenda del día y de la semana (vista calendario), próximas citas y alertas de topes.
- **Servicios**: CRUD con el patrón `if action`.
- **Profesionales**: horario, bloqueos, servicios que presta, conexión con Google (botón "Conectar Google Calendar").
- **Citas**: listado con filtros (fecha, profesional, estado) y acciones confirmar, reprogramar, cancelar y marcar asistencia.
- **Página pública de reserva**: elegir servicio, luego profesional (o "cualquiera"), luego día y franja, luego datos y confirmación.
- **Gestión desde el correo**: página pública por token para cancelar o reprogramar.
- **Métricas** (fase 2).

## 7. Decisiones abiertas (para `grilling` antes de implementar)

1. ¿Un calendario central del negocio o el Google de cada profesional (OAuth por usuario)?
2. ¿Rubro? (consultorio, estudio, asesorías…): define si hay pagos, si hay sala o recurso físico y si importa la inasistencia.
3. ¿El cliente reserva solo (página pública) o solo el staff agenda?
4. ¿Hay pago o seña al reservar? (Prelude no lo tiene; muchos sistemas de citas sí.)
5. ¿Recordatorios solo por correo, o también WhatsApp?
6. ¿Una sede o varias? ¿Recursos físicos (salas, equipos) que también se reservan?
7. ¿Qué pasa si alguien mueve la cita directamente en Google: se acepta o se revierte?

## 8. Fuentes

- SelectSoftwareReviews — Prelude: https://www.selectsoftwarereviews.com/reviews/interview-scheduling-prelude
- GetApp — Prelude: https://www.getapp.co.uk/software/2050573/prelude
- Software Advice — Prelude: https://www.softwareadvice.co.uk/software/43216/prelude
- Cronofy — alternativa a Prelude: https://www.cronofy.com/api/markdown/prelude-alternative
- Zoom Marketplace — Prelude: https://marketplace.zoom.us/apps/486wT26SSF-16fbRBRDHGA

Relacionado: skill `agendamiento-google` (cómo integrar Calendar y Gmail).
