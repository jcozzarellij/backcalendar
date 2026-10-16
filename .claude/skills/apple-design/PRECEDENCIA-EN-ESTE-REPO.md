# Cómo se aplica `apple-design` en backmanageria

Decisión de Héctor (2026-08-28): **manda el CLAUDE.md del repo.**

## Se toma el método de interacción

Secciones 1–11 y 13–17: respuesta en el pointer-down, arrastre 1:1, interrumpibilidad,
comportamiento por springs en vez de duraciones, traspaso de velocidad, consistencia espacial
(entrar y salir por el mismo camino, anclar al origen), rubber-banding, `prefers-reduced-motion`,
tipografía con tracking dependiente del tamaño, y las cuatro clases de feedback
(estado / completado / aviso / error) con etiquetas directas.

## §12 (Materials & depth): prohibida en la plataforma, permitida en el landing público

Decisión de Héctor (2026-08-28, segunda pasada): **el landing público se queda con el glass.**

- **Plataforma autenticada** (`base.html`, paleta `--mo-*`, monitoreo, wallet, notebook, CRM):
  sigue vigente la prohibición del CLAUDE.md — nada de `backdrop-filter`, capas translúcidas ni
  máscaras con degradado. Ese barrido ya se hizo y no se deshace. La jerarquía se expresa con
  superficies sólidas, el borde `--mo-borde` y sombra corta y contenida.
- **Portal público** (`baselanding.html`, `landing.css`, paleta `--lnd-*`): tiene identidad visual
  propia y el `backdrop-filter` es parte de ella (navbar, sheet del chat, tarjetas, FAQ). Se
  mantiene. La regla «nunca degradados» **sí sigue aplicando también acá**: la excepción es la
  translucidez, no los degradados.

Al tocar el landing, respetar las dos reglas de §12 que evitan que el glass se rompa: no apilar una
superficie translúcida clara sobre otra, y que las superficies grandes lean como más gruesas
(más blur y sombra más profunda) que las chicas.

## Y tampoco

- Nada de Tailwind ni de utilidades que la skill asume: el repo es Bootstrap 5 con su grid.
  El landing público no usa Bootstrap: es CSS propio en `static/css/public/landing.css`.
- El CSS va en `static/css/<app>/` con cache-busting, nunca en `<style>` dentro del template.
- Sin comentarios en templates, CSS ni JS.
- Copy en español.

## Qué se aplicó ya

`.ai/docs/landing_publico.md` registra la pasada del 2026-08-28 sobre el landing: tacto en
pointer-down, bottom-sheet arrastrable con proyección de momento y springs, escala tipográfica en
`rem`/`clamp`, accesibilidad del chat y tope a las animaciones en bucle.
