---
name: spec
description: Abre un spec de diseño, conduce la conversación hacia él y lo guarda en specs/<área>/ antes de planificar. Invocar al empezar una feature nueva de backcalendar.
disable-model-invocation: true
argument-hint: <qué vamos a construir>
---

# /spec

Specs de diseño de backcalendar. Se invoca **una vez**, al inicio: el usuario da el contexto, la conversación que sigue se vuelve el spec y se guarda cuando el diseño se asienta. Es el primer paso del flujo del repo: **spec → grilling → implementar → revisión del usuario → verificación a fondo** (ver `CLAUDE.md`, «Dónde se verifica a fondo»).

El archivo es el **ancla**: una entrevista larga desborda el contexto; el archivo no. Tras una compactación o un desvío, releerlo.

Todo en **español**.

## 1. Abrir

Fijar el **área**: `ls -d specs/*/` y elegir la que encaja (hoy la carpeta puede no existir: crearla). Áreas naturales del repo: `agendamiento`, `autenticacion`, `seguridad`, `area_geografica`, `public`, `pwa`; lo que no encaja va a `specs/varios/` y funda área propia cuando llega un segundo spec del mismo tema.

Escribir `specs/<área>/YYYY-MM-DD-<nombre-kebab>.md` con la plantilla, `Estado: Borrador` y un `## Contexto` con lo que dio el usuario, en sus propios términos. Índices y `git add` esperan al paso 3.

## 2. Entrevistar

Usar la skill `grilling` (rondas numeradas, cada pregunta con **recomendación explícita** y su porqué). Criterio para recomendar: datos consistentes, error imposible, trazabilidad. Cubrir lo que el contexto no resolvió:

- **Alcance**: qué entra y, explícitamente, qué queda fuera.
- **Datos**: ¿modelo o campo nuevo? Hereda `ModeloBase`; si es evidencia, `RegistroInmutable`; choices a nivel de módulo; textos largos en tabla + seeder en `scripts/`. Un valor parametrizable arranca como constante; el campo viene después de validarlo.
- **Integración**: qué vistas, acciones y plantillas existentes se tocan. Por defecto, recomendar una acción nueva antes que modificar un `add`/`change` que funciona.
- **Acceso**: qué grupo (`Administrador`, `Staff`, ...) ve la pantalla vía `GroupModulo`; si es global, `@solo_administrador`.
- **Estados y UX**: éxito, error, vacío y sin permiso.
- **Riesgos**: qué se rompe si falla a medias, qué es irreversible, si toca algo de la lista «a fondo» de `CLAUDE.md` (migraciones en producción, contabilidad, gates de seguridad, registros de evidencia).

**Registrar decisiones al momento**, en `## Decisiones`, en el mismo turno: qué se eligió, **por qué** y **qué alternativa se descartó**.

La entrevista termina cuando se pueden nombrar tres cosas: qué archivos cambian y cómo; el primer y el último paso ejecutable; el observable que prueba que funciona. Entonces proponer:

> Ya tengo archivos, pasos y criterio de verificación. ¿Guardamos el spec?

## 3. Guardar

Con el sí del usuario, en este orden (el plan mode bloquea escrituras):

1. Completar Contexto, Decisiones, Archivos, Criterios de aceptación.
2. Cambiar `Borrador` por el estado real.
3. Agregar la fila a `specs/<área>/README.md` y la línea del área a `specs/README.md` si es nueva.
4. `git add` del spec y de cada README nuevo (nunca commit).
5. `EnterPlanMode` y luego `ExitPlanMode` con el plan derivado del spec.

## Plantilla

```markdown
# <Título>

**Área:** <área> · **Fecha:** YYYY-MM-DD · **Estado:** Borrador

## Contexto

Qué existe hoy, con rutas `archivo.py:línea`, y qué problema abre este trabajo.

## Decisiones

1. **<Decisión>** — qué se eligió, por qué, y qué alternativa se descartó.

## Archivos

| Archivo | Cambio |
|---|---|

## Criterios de aceptación

- [ ] Observable que prueba que quedó hecho.
```

Si un spec reemplaza a otro: `**Reemplaza:** [<título>](<archivo>.md)` bajo el encabezado, y el viejo pasa a `Disuelto` con `**Reemplazado por:**`.

## Estados

| Estado | Significa |
|---|---|
| `Borrador` | Diseño en curso. Fuera de índices y de git. |
| `Planificado` | Diseño cerrado, sin implementar. |
| `Implementado, pendiente de verificación` | Escrito; el desarrollador aún no lo probó en PyCharm. |
| `Verificado` | Probado y funcionando. |
| `Disuelto` | Descartado o absorbido por otro spec, con el enlace. |

## Índices

`specs/<área>/README.md`, una tabla, lo más nuevo al final:

```markdown
| Fecha | Spec | Entrega | Estado |
|---|---|---|---|
| 2026-10-08 | [Reserva de citas](2026-10-08-reserva-de-citas.md) | Cliente elige horario libre y recibe invitación | Planificado |
```

`specs/README.md`: las áreas, qué cubre cada una y el enlace a su índice. La cronología vive en los nombres de archivo y en `git log`.
