# Diseño de interfaces nuevas

Pantalla nueva, template nuevo, rediseño de una vista o CSS de una feature. Invocar sin que el usuario lo pida:

1. `frontend-design` — plan de tokens (color, tipo, layout, firma) antes de codificar; autocrítica contra defaults genéricos.
2. `high-end-visual-design` — acabado premium: espaciado, sombras, jerarquía, micro-interacciones.
3. `web-design-guidelines` — al terminar, auditar contra su checklist (accesibilidad, focus, responsive).

Retoque menor (columna, botón, badge): solo `web-design-guidelines`. Identidad visual real del panel: skill `diseno-backcalendar`.

## Precedencia

Las reglas del repo mandan sobre esas skills. De ellas se toma el método (dos pasadas, restraint, copy en voz activa, estados vacíos que invitan a actuar), nunca una estética que las viole:

- Superficies planas y colores sólidos; degradados, mesh gradients y glassmorphism están descartados (el usuario descartó el vidrio el 2026-10-08).
- Páginas públicas de Turno: fondo blanco, fuente Geist, estilo Calendly/Apple. Foto de fondo con velo de color sólido permitida.
- Bootstrap 5 con su grid (las skills asumen Tailwind), paleta e identidad existentes, CSS en `static/css/<app>/`, copy en español. Convenciones de archivos y componentes: `docs/agentes/templates.md`.
