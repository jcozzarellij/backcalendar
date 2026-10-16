# MCP Postgres de backcalendar

Servidor MCP que le permite a Claude Code explorar la base de datos PostgreSQL del proyecto. Las lecturas son libres; cualquier escritura (INSERT, UPDATE, DELETE, DDL) exige la confirmación del programador.

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado (gestiona Python y las dependencias; no hace falta crear un venv a mano).
- Python 3.10 o superior (uv lo descarga solo si no lo tienes).
- Claude Code.
- Acceso de red a la base de datos PostgreSQL y un usuario con permisos.

## Puesta en marcha

1. Instalar las dependencias:

   ```
   cd .claude/mcp_postgres
   uv sync
   ```

2. Crear el archivo de credenciales a partir de la plantilla:

   ```
   cp .env_template .env
   ```

   En PowerShell: `Copy-Item .env_template .env`.

3. Completar `.env` con los datos de la base:

   | Variable | Descripción | Por defecto |
   |---|---|---|
   | `POSTGRES_HOST` | Servidor de la base | `localhost` |
   | `POSTGRES_PORT` | Puerto | `5432` |
   | `POSTGRES_DBNAME` | Nombre de la base | (vacío) |
   | `POSTGRES_USER` | Usuario | (vacío) |
   | `POSTGRES_PASSWORD` | Contraseña | (vacío) |
   | `POSTGRES_SSLMODE` | `disable`, `prefer`, `require`... | `prefer` |
   | `MAX_FILAS` | Máximo de filas por consulta | `200` |
   | `TIMEOUT_MS` | Tiempo máximo por sentencia, en ms | `15000` |

   Los valores son los mismos de `POSTGRES_*` en `credenciales.json` del proyecto. `.env` está ignorado por git: nunca lo subas.

4. Abrir Claude Code en la raíz del repositorio. El servidor `postgres` está declarado en `.mcp.json`; Claude Code pedirá aprobarlo la primera vez.

5. Verificar la conexión con `/mcp` (debe aparecer `postgres` conectado) y luego con:

   ```
   /db lista los esquemas disponibles
   ```

## Uso

El comando `/db` (definido en `.claude/commands/db.md`) usa el contexto de la conversación y el texto que le pases:

```
/db cuántas citas hay por estado esta semana
/db revisa por qué el usuario 15 no ve el módulo agenda
/db
```

Sin argumento, deduce qué consultar a partir de la conversación.

## Herramientas

| Herramienta | Qué hace | Confirmación |
|---|---|---|
| `pg_listar_esquemas` | Lista los esquemas de usuario | No |
| `pg_listar_tablas` | Lista tablas y vistas con filas estimadas | No |
| `pg_describir_tabla` | Columnas, restricciones e índices | No |
| `pg_consultar` | Ejecuta `SELECT`, `WITH`, `SHOW`, `EXPLAIN`, `VALUES`, `TABLE` | No |
| `pg_ejecutar_con_confirmacion` | Ejecuta sentencias que modifican la base | Sí, siempre |

## Seguridad

- `pg_consultar` corre en una transacción `READ ONLY`: PostgreSQL rechaza cualquier escritura, aunque la consulta intente disfrazarla.
- Solo se permite una sentencia por llamada, con límite de filas y de tiempo.
- `pg_ejecutar_con_confirmacion` muestra el SQL exacto y el motivo, y no ejecuta nada si no confirmas. Si falla, la transacción se revierte. Claude Code además pide permiso para usarla: no la agregues a la lista de herramientas permitidas.
- Recomendado: usa en `.env` un usuario de base de datos de solo lectura. Así ninguna herramienta puede escribir aunque se confirme por error. Para escribir, usa otro usuario con permisos.
- No apuntes este MCP a producción con un usuario con permisos de escritura.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `/mcp` muestra `postgres` fallido | Falta `uv` en el PATH o no corriste `uv sync`. Prueba `uv run --directory .claude/mcp_postgres python server.py` en una terminal para ver el error. |
| `connection refused` o `timeout` | Revisa `POSTGRES_HOST`, `POSTGRES_PORT`, VPN o firewall. |
| `password authentication failed` | Revisa usuario y contraseña en `.env`. |
| `SSL required` | Pon `POSTGRES_SSLMODE=require`. |
| Cambié `.env` y no se nota | Reinicia Claude Code: el servidor lee `.env` al arrancar. |
| La escritura responde que el cliente no soporta confirmación | Actualiza Claude Code a una versión con soporte de elicitation. No se ejecutó nada. |

## Estructura

```
.claude/mcp_postgres/
├── server.py          código del servidor
├── pyproject.toml     dependencias
├── uv.lock            versiones fijadas (se versiona)
├── .env_template      plantilla de credenciales (se versiona)
├── .env               credenciales reales (ignorado por git)
└── README.md
```
