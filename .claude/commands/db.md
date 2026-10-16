---
description: Consulta la base de datos PostgreSQL con el MCP postgres usando el contexto de la conversación.
argument-hint: <qué quieres buscar o verificar>
allowed-tools: mcp__postgres__pg_listar_esquemas, mcp__postgres__pg_listar_tablas, mcp__postgres__pg_describir_tabla, mcp__postgres__pg_consultar
---

Investigar en la base de datos usando el MCP `postgres`.

Pedido del usuario: `$ARGUMENTS`

Si el pedido está vacío, deducir qué consultar a partir de la conversación (modelos, tablas, errores, registros o datos mencionados) y decir qué se va a buscar.

### Método

1. Usar el contexto de la conversación: modelos Django, nombres de tablas, ids, errores o hipótesis ya mencionados. No volver a derivar lo ya establecido.
2. Si el nombre de la tabla no es seguro, `pg_listar_tablas`. Los modelos Django van como `<app>_<modelo en minúsculas>` (ej. `autenticacion_usuario`, `agenda_cita`). Confirmar columnas con `pg_describir_tabla` antes de armar la consulta.
3. Consultar con `pg_consultar`: una sola sentencia, solo las columnas necesarias, `WHERE` y `LIMIT` explícitos. Excluir filas dadas de baja con `status = true` salvo que el pedido sea justo ver las eliminadas.
4. Si la primera consulta no alcanza, encadenar las siguientes necesarias; no preguntar entre consultas de lectura.

### Reglas

- Solo lectura. No usar `pg_ejecutar_con_confirmacion` desde este comando. Si el pedido implica insertar, actualizar o borrar, mostrar el SQL propuesto y esperar que el usuario pida ejecutarlo.
- No mostrar contraseñas, tokens ni hashes: omitir esas columnas en el `SELECT`.
- No inventar resultados. Si una consulta falla o devuelve vacío, decirlo y probar otra ruta.

### Respuesta

En español. Primero el hallazgo que responde el pedido; después el SQL usado y las tablas consultadas. Si el resultado se truncó, avisarlo.
