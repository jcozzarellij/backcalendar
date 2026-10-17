# Diseño de interfaces nuevas

Pantalla nueva, template nuevo, rediseño de una vista o CSS de una feature. Dos sistemas visuales; elige por la plantilla base:

- Extiende `templates/public/base_landing.html` (landing, catálogo, pantalla pública rediseñada): skill `design-guidelines-landing`.
- Extiende `templates/base.html` (panel) o es acceso, portal o legales aún sin migrar: skill `design-guidelines-panel`.

Invocar sin que el usuario lo pida:

1. `frontend-design`: plan de tokens (color, tipo, layout, firma) antes de codificar; autocrítica contra defaults genéricos.
2. `high-end-visual-design`: acabado premium: espaciado, jerarquía, micro-interacciones.
3. `web-design-guidelines`: al terminar, auditar contra su checklist (accesibilidad, focus, responsive).

Retoque menor (columna, botón, badge): solo `web-design-guidelines`.

## Precedencia

Las reglas del repo y el sistema elegido (`DESIGN-landing.md` o `DESIGN-panel.md`) mandan sobre esas skills. De ellas se toma el método (dos pasadas, restraint, copy en voz activa, estados vacíos que invitan a actuar), nunca una estética que las viole:

- Degradados y mesh gradients descartados. El vidrio solo existe en la barra del landing.
- Bootstrap 5 con su grid (las skills asumen Tailwind), paleta e identidad existentes, CSS en `static/css/<app>/`, copy en español. Convenciones de archivos y componentes: `docs/agentes/templates.md`.
