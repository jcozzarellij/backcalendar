---
name: Turno de Exducere Online
description: Landing público de Turno, el mostrador: fondo nube con la hoja verde del logo, tickets de papel troquelado, barra de vidrio, azul que informa y verde que actúa; Roboto en titulares y cuerpo.
colors:
  azul: "#005082"
  azul-oscuro: "#003a5f"
  azul-medio: "#0a6aa6"
  verde: "#67BD01"
  verde-accion: "#3f7f00"
  verde-accion-hover: "#336600"
  fondo-suave: "#f3f4f6"
  papel: "#ffffff"
  tinta: "#071a31"
  tinta-panel: "#1A2B3C"
  texto-publico: "#3a4b5c"
  gris: "#5f6d77"
  borde: "#e4e6e9"
  nube: "#E6F0F5"
  nube-oscura: "#d6e6ef"
  linea-publica: "#c3d4df"
  vidrio: "rgba(255, 255, 255, 0.6)"
typography:
  display:
    fontFamily: "Roboto, system-ui, sans-serif"
    fontSize: "clamp(2.2em, 2.4vw + 1.3em, 3.7em)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  headline-publico:
    fontFamily: "Roboto, system-ui, sans-serif"
    fontSize: "clamp(1.5em, 1.2vw + 1.1em, 2.1em)"
    fontWeight: 800
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  ticket:
    fontFamily: "Roboto, system-ui, sans-serif"
    fontSize: "1.65em"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  body-publico:
    fontFamily: "Roboto, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "19px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  pildora: "999px"
  ticket: "20px"
  vidrio: "22px"
  menu: "14px"
  parte: "16px"
components:
  nav-vidrio:
    backgroundColor: "{colors.vidrio}"
    textColor: "{colors.tinta-panel}"
    rounded: "{rounded.vidrio}"
    padding: "10px 12px 10px 20px"
    height: "72px"
  menu-idioma:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta-panel}"
    rounded: "{rounded.menu}"
    padding: "0 16px"
    height: "48px"
  ticket:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta-panel}"
    rounded: "{rounded.ticket}"
    padding: "1.4em 1.6em"
  ticket-agendar:
    backgroundColor: "{colors.verde-accion}"
    textColor: "{colors.papel}"
    rounded: "{rounded.pildora}"
    padding: "0.55em 1.6em"
    height: "56px"
  ticket-parte:
    backgroundColor: "{colors.nube}"
    textColor: "{colors.tinta-panel}"
    rounded: "{rounded.parte}"
    padding: "0.8em 0.8em 0.8em 1.1em"
  nav-btn:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
    rounded: "{rounded.pildora}"
    padding: "9px 20px"
    height: "44px"
---

# Design System: Turno de Exducere Online

Turno tiene dos sistemas visuales. Este archivo es el índice y lleva los tokens del landing.

- **Landing público** (`/`, `/catalogo/`, páginas que extienden `templates/public/base_landing.html`): `DESIGN-landing.md` y skill `design-guidelines-landing`.
- **Panel** (`/agenda/…`, Bootstrap 5.3 con `--bs-*`) y pantallas públicas aún sin migrar (acceso, portal, legales): `DESIGN-panel.md` y skill `design-guidelines-panel`.
