# Cómo se aplica `improve-codebase-architecture` en backmanagercne

Instalada el 2026-09-24. Solo corre a pedido (`/improve-codebase-architecture`). **Manda el repo.**

## Ajustes

- El reporte HTML no va en el repo (la skill ya lo escribe en el directorio temporal). Si se quiere
  compartir, se publica como Artifact.
- Las skills que invoca (`codebase-design`, `grilling`, `domain-modeling`) están instaladas, cada una
  con su propia nota de precedencia.
- El glosario del dominio y las decisiones no están en `CONTEXT.md` ni en `docs/adr/`: están en
  `.ai/docs/` (empezar por `onboarding_arquitectura.md`, el índice es `_index.md`). Una decisión nueva
  se registra como doc del vault, con su frontmatter y enlazada desde `_index.md`, no como ADR suelto.
- Toda propuesta respeta las reglas duras del CLAUDE.md: estructura `if action` en las views, helpers
  de dominio en `funciones_*.py`, `ModeloBase`, choices a nivel de módulo, scripts en `scripts/`.
