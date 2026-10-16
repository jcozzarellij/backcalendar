# Cómo se aplica `domain-modeling` en backmanagercne

Instalada el 2026-09-24. **Manda el repo.**

## Se toma

- La disciplina: cuestionar términos ambiguos, proponer el término canónico, probar las relaciones con
  escenarios de borde y contrastar lo que se dice con lo que hace el código.

## Dónde se escribe en este repo

- **No se crean `CONTEXT.md`, `CONTEXT-MAP.md` ni `docs/adr/`.** El modelo del dominio vive en el vault
  de Obsidian `.ai/docs/`:
  - Glosario: sección de glosario de `onboarding_arquitectura.md`.
  - Decisiones: un doc del vault con frontmatter (`tags`, `estado`, `actualizado`, `resumen`, `codigo:`),
    enlazado desde `_index.md` y referenciado con `[[nombre]]`.
- Al tocar un doc, actualizar `estado` y `actualizado`, y validar con `python scripts/validar_docs.py`.
- Términos y docs en español; los nombres de modelos del dominio llevan sufijo `CNE` (`ConexionCNE`,
  `CursoCNE`, `AtencionCNE`…).
