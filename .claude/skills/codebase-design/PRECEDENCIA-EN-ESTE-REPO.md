# Cómo se aplica `codebase-design` en backmanagercne

Instalada el 2026-09-24. **Manda el repo.**

- Se toma el vocabulario (módulo, interfaz, profundidad, seam, adapter, leverage, localidad) y sus
  pruebas (test de borrado, «la interfaz es la superficie de test», «un adapter es un seam hipotético,
  dos es uno real»).
- Las propuestas respetan las reglas duras del CLAUDE.md: views con estructura `if action` y CRUD
  inline, lógica de dominio reutilizable en `funciones_*.py`, `ModeloBase`, choices a nivel de módulo,
  dispatch por `ConsultasAjax`, scripts en `scripts/`.
- El patrón «design it twice» con subagentes en paralelo se usa solo si el usuario lo pide.
