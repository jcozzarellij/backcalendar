---
name: Turno de Exducere Online, panel
description: Panel interno de Turno sobre Bootstrap 5.3: fondo nube, tinta azulada, Geist, azul que informa, verde que confirma y tres sombras tonales.
colors:
  azul: "#005082"
  azul-oscuro: "#003a5f"
  azul-velo: "rgba(0, 80, 130, 0.1)"
  azul-borde-suave: "#b3cbdb"
  verde: "#67BD01"
  verde-hover: "#5aa601"
  nube: "#E6F0F5"
  tinta-panel: "#1A2B3C"
  pizarra: "#64748B"
  rojo: "#D93838"
  ambar: "#F59E0B"
  cian: "#06B6D4"
  papel: "#ffffff"
typography:
  body-panel:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  titulo-panel:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontWeight: 600
    letterSpacing: "-0.02em"
rounded:
  sm: "0.55rem"
  md: "0.85rem"
  lg: "1.1rem"
  xl: "1.6rem"
  xxl: "2.25rem"
  pildora: "50rem"
components:
  button-primary:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
  button-success:
    backgroundColor: "{colors.verde}"
    textColor: "{colors.tinta-panel}"
  celda-turno-pressed:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
---

# Design System: Panel de Turno

Los tokens viven en `static/base_adicional.css` (`:root`, variables `--turno-*` y `--bs-*`); ese archivo manda sobre este. Cómo armar una pantalla (listados, modales, KPIs): skill `design-guidelines-panel`. Landing público: `DESIGN-landing.md`.

## Base

- Tema `static/assets_riz/css/bootstrap.min.css` (Bootstrap 5.3.3) + `app.min.css`; ajustes en `static/base_adicional.css` y `static/base_tablas.css`.
- Fondo `--bs-body-bg` nube `#E6F0F5`, texto `--bs-body-color` tinta `#1A2B3C`.
- Geist en todo (`--bs-font-sans-serif`), incluidos `h1–h6`, `.page-title` y `.modal-title` en 600 con −0.02em. El tema trae Be Vietnam Pro; `base_adicional.css` lo reemplaza.
- Íconos: Font Awesome 5 y Line Awesome.

## Colors

- **Azul** `--bs-primary` `#005082` (hover `#003a5f`): `btn-primary`, enlaces, ítem activo de la barra lateral (velo al 12 %), celda de turno seleccionada, marca del panel.
- **Verde** `--bs-success` `#67BD01` (hover `#5aa601`): `btn-success`, el botón de acción principal de la pantalla (guardar, nuevo). El texto sobre este verde es siempre tinta; `.badge.bg-success` y `.text-bg-success` también.
- **Peligro** `--bs-danger` `#D93838`: error, borrado, cancelar en modales. **Aviso** `--bs-warning` `#F59E0B`. **Info** `--bs-info` `#06B6D4`. **Secundario** `--bs-secondary` pizarra `#64748B`: texto auxiliar.
- Cada color trae `*-bg-subtle`, `*-border-subtle` y `*-text-emphasis`; úsalos para pills, contenedores de icono y alertas suaves en vez de inventar tintes.
- En CSS propio referencia `var(--bs-…)` o `var(--turno-…)`, nunca hex sueltos.
- `.badge-primary` y `.badge-success` (clases heredadas del tema, `#0d6efd` y `#16C784`) siguen en uso; en pantallas nuevas usa `badge bg-*`.

### Named Rules

**El único verde.** Un `btn-success` principal por pantalla o modal.

**Tinta sobre verde.** Blanco sobre `#67BD01` no cumple contraste.

**El azul que informa.** Nunca fondo de página ni de tarjeta; es botón, enlace, icono o ítem activo.

## Elevation

Tres sombras tonales de la tinta (`rgba(26, 43, 60, …)`), nunca negras ni de desplazamiento duro:

- `--bs-box-shadow-sm` `0 0.15rem 0.4rem` al 6 %: `.card` en reposo.
- `--bs-box-shadow` `0 0.5rem 1.25rem` al 8 %: `.card:hover`, `.dropdown-menu` (sin borde).
- `--bs-box-shadow-lg` `0 1rem 2rem` al 12 %: `.modal-content` (sin borde).

Sin degradados ni vidrio. Radios: `--bs-border-radius` 0.85 rem (sm 0.55, lg 1.1, xl 1.6, pill 50). `.form-control` siempre con fondo blanco (regla global `!important`).

## Tablas

`static/base_tablas.css`: encabezado `rgb(243,243,243)`, bordes `#e4e7ea`, hover `#f2f4f5`, fila enfocada `.tableRowFocus`.

## Rejilla de turnos

Celdas de 2.1 rem de alto, papel con borde 1 px y radio `--bs-border-radius-sm`; en hover el borde pasa a `#b3cbdb` y aparece la hora en pizarra; `aria-pressed="true"` las llena de azul con texto blanco. Foco: anillo verde de 3 px.

## Pendiente de migrar al landing

Siguen en el registro anterior (Geist, fondo blanco cálido `#fcfbf8`, papel con borde de 1 px `#e4e6e9`, sin sombras, texto base 17 px, píldoras de 48 px) hasta su rediseño: solo el inicio de sesión (`/login/`, `static/css/public/auth.css`). Al rediseñarlo, pasa a `base_landing.html` y a las reglas de `DESIGN-landing.md`. Ya están en esa línea, con `static/css/public/reserva.css`: el portal (agendar, mi cita, mis citas, ventana para incrustar y enlace inválido), recuperar contraseña y usuario, cambiar contraseña y las páginas legales (`public/legal.html`).

## Don'ts

- Sin `btn-outline-*`, degradados, franjas de color a la izquierda de tarjetas, `<style>` ni comentarios en HTML, CSS o JS.
- Sin sombras fuera de las tres definidas.
- Sin paleta nueva fuera de los tokens.
