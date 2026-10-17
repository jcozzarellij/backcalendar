# CLAUDE.md — backcalendar

Backend Django 5.2 LTS monolítico (Python 3.11, PostgreSQL, solo WSGI: sin Celery, Redis ni ASGI; cache `LocMemCache`).
Usuario: `autenticacion.Usuario`. Acceso al panel = `is_staff`; el alcance lo dan los grupos vía `GroupModulo`; los
superusuarios ven todos los módulos.

Responder siempre en **español** (chat, código visible, copy de UI, logs, excepciones), también bajo modos comprimidos.
Los nombres de variables backend van en español (`criterio`, `filtro`, `listado`).

## Reglas duras

- Migraciones existentes: intocables. `makemigrations`, `migrate` y `showmigrations` están permitidos solo para cambios
  de modelos, siempre aditivos; ante «tabla ya existe», verificar por introspección antes de `--fake`.
- El developer corre el servidor desde PyCharm. Fuera de lo anterior, ningún management command (`runserver`, `flush`,
  `sqlflush`, `dbshell` con DDL).
- Git: `git add <archivo>` apenas se crea un `.html`, `.css` o `.py` nuevo (no para modificados). Sin `commit`, `push`
  ni operaciones destructivas.
- `credenciales.json` y cualquier archivo de secretos: sin leer ni modificar (`credenciales_template.json` lista las
  claves).
- UI siempre: todo `<select>` lleva clase `select2`; botones sólidos (`btn-primary`, `btn-danger`…), nunca
  `btn-outline-*`; sin comentarios en templates, CSS ni JS. Detalle en `docs/agentes/templates.md`.
- Estilo: lo verifica el developer; sin auto-formato ni lint.
- Playwright (MCP `playwright` de `.mcp.json`): nunca usarlo por iniciativa propia ni como paso de verificación; solo
  cuando el usuario lo pida explícitamente. Sus archivos van a `.playwright-mcp/` (ignorado en git).
- Todo script (seeder, CLI, demo) va en `scripts/` de la raíz, con bootstrap `Path(__file__).resolve().parents[1]`;
  nunca dentro de una app. Ejecutar seeders cuando la tarea lo pida; si uno no es idempotente, su docstring lo advierte.

## Verificar

Correr `pycheck` (sangría y sintaxis). El developer revisa en el navegador y comunica correcciones.

## Punteros

- **Python/Django** (views, modelos, forms, uploads, ORM, consultas AJAX): leer `CODING_STANDARDS.md`. Feature o app
  nueva: antes, skill `arquitectura-backcalendar`.
- **Templates, CSS, JS, botones, selects** (cualquier `.html`, `.css`, `.js`): leer `docs/agentes/templates.md`.
- **Pantalla nueva o rediseño visual**: leer `docs/agentes/diseno-frontend.md`.
- **Identidad visual**: landing público → skill `design-guidelines-landing`; panel → skill `design-guidelines-panel` (índice en `DESIGN.md`).
- **`agenda/`** (micrositio, turnos, citas): leer `docs/agentes/agenda.md`.
- Estudios previos de agendamiento: `docs/` y `.ai/docs/`. Revisión de diff contra reglas: agente `revisor-reglas`, solo
  si se pide.
