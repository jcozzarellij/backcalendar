import json
import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent / ".env")

mcp = FastMCP("postgres_backcalendar")

ESQUEMAS_SISTEMA = ("pg_catalog", "information_schema", "pg_toast")
MAX_FILAS = int(os.getenv("MAX_FILAS", "200"))
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "15000"))
PATRON_LECTURA = re.compile(r"^\s*\(?\s*(select|with|show|explain|values|table)\b", re.IGNORECASE)
ANOTACION_LECTURA = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


class Confirmacion(BaseModel):
    confirmar: bool = Field(description="Marcar para ejecutar la sentencia mostrada arriba")


def conectar():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DBNAME", ""),
        user=os.getenv("POSTGRES_USER", ""),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
        connect_timeout=10,
        options=f"-c statement_timeout={TIMEOUT_MS}",
    )


def filas_a_json(cur, limite):
    if cur.description is None:
        return {"filas_afectadas": cur.rowcount}
    columnas = [c.name for c in cur.description]
    filas = cur.fetchmany(limite + 1)
    truncado = len(filas) > limite
    filas = filas[:limite]
    return {
        "columnas": columnas,
        "total_devuelto": len(filas),
        "truncado": truncado,
        "filas": [dict(zip(columnas, f)) for f in filas],
    }


def salida(datos):
    return json.dumps(datos, default=str, ensure_ascii=False, indent=2)


def leer(consulta, params=None, limite=MAX_FILAS):
    with conectar() as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute(consulta, params)
            return filas_a_json(cur, limite)


@mcp.tool(annotations=ANOTACION_LECTURA)
def pg_listar_esquemas() -> str:
    """Lista los esquemas de usuario de la base de datos (excluye los del sistema)."""
    try:
        return salida(leer(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name <> ALL(%s) AND schema_name NOT LIKE 'pg\\_%%' ORDER BY 1",
            (list(ESQUEMAS_SISTEMA),),
        ))
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations=ANOTACION_LECTURA)
def pg_listar_tablas(esquema: str = "public") -> str:
    """Lista tablas y vistas de un esquema con su cantidad estimada de filas.

    Args:
        esquema: nombre del esquema (por defecto 'public').
    """
    try:
        return salida(leer(
            "SELECT c.relname AS nombre, CASE c.relkind WHEN 'r' THEN 'tabla' WHEN 'v' THEN 'vista' "
            "WHEN 'm' THEN 'vista_materializada' WHEN 'p' THEN 'tabla_particionada' END AS tipo, "
            "c.reltuples::bigint AS filas_estimadas "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relkind IN ('r','v','m','p') ORDER BY c.relname",
            (esquema,),
            limite=5000,
        ))
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations=ANOTACION_LECTURA)
def pg_describir_tabla(tabla: str, esquema: str = "public") -> str:
    """Describe columnas, restricciones (PK, FK, unique, check) e índices de una tabla.

    Args:
        tabla: nombre de la tabla o vista.
        esquema: nombre del esquema (por defecto 'public').
    """
    try:
        columnas = leer(
            "SELECT column_name, data_type, is_nullable, column_default, character_maximum_length "
            "FROM information_schema.columns WHERE table_schema = %s AND table_name = %s "
            "ORDER BY ordinal_position",
            (esquema, tabla),
            limite=1000,
        )
        if not columnas["filas"]:
            return f"Error: no existe {esquema}.{tabla}. Usa pg_listar_tablas para ver los nombres."
        restricciones = leer(
            "SELECT con.conname AS nombre, con.contype AS tipo, pg_get_constraintdef(con.oid) AS definicion "
            "FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s AND c.relname = %s "
            "ORDER BY con.contype, con.conname",
            (esquema, tabla),
            limite=1000,
        )
        indices = leer(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
            (esquema, tabla),
            limite=1000,
        )
        return salida({
            "columnas": columnas["filas"],
            "restricciones": restricciones["filas"],
            "indices": indices["filas"],
        })
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations=ANOTACION_LECTURA)
def pg_consultar(consulta: str, limite: int = 50) -> str:
    """Ejecuta una consulta de SOLO LECTURA (SELECT, WITH, SHOW, EXPLAIN, VALUES, TABLE).

    Corre dentro de una transacción READ ONLY: PostgreSQL rechaza cualquier escritura.
    Si necesitas INSERT/UPDATE/DELETE/DDL usa pg_ejecutar_con_confirmacion.

    Args:
        consulta: una sola sentencia SQL de lectura.
        limite: máximo de filas a devolver (1 a MAX_FILAS, por defecto 50).
    """
    consulta = consulta.strip().rstrip(";")
    if ";" in consulta:
        return "Error: solo se permite una sentencia por llamada."
    if not PATRON_LECTURA.match(consulta):
        return "Error: pg_consultar solo acepta lecturas. Usa pg_ejecutar_con_confirmacion para escrituras."
    try:
        return salida(leer(consulta, limite=max(1, min(limite, MAX_FILAS))))
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False})
async def pg_ejecutar_con_confirmacion(sentencia: str, motivo: str, ctx: Context) -> str:
    """Ejecuta una sentencia que MODIFICA la base (INSERT, UPDATE, DELETE, DDL, TRUNCATE, etc.).

    El programador debe confirmar la sentencia exacta antes de que se ejecute. Corre en una
    transacción que se revierte si falla. No usar para lecturas: usa pg_consultar.

    Args:
        sentencia: una sola sentencia SQL.
        motivo: por qué se necesita el cambio, en una frase.
    """
    sentencia = sentencia.strip().rstrip(";")
    if not sentencia or ";" in sentencia:
        return "Error: se requiere exactamente una sentencia."
    try:
        respuesta = await ctx.elicit(
            message=f"CONFIRMAR ESCRITURA EN LA BASE DE DATOS\n\nMotivo: {motivo}\n\nSQL:\n{sentencia}",
            schema=Confirmacion,
        )
    except Exception as e:
        return f"Error: el cliente no soporta confirmación interactiva ({e}). No se ejecutó nada."
    if respuesta.action != "accept" or not respuesta.data.confirmar:
        return "Cancelado: el programador no confirmó. No se ejecutó nada."
    try:
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sentencia)
                resultado = filas_a_json(cur, MAX_FILAS)
        return salida({"ejecutado": True, **resultado})
    except Exception as e:
        return f"Error: {e}. La transacción se revirtió."


if __name__ == "__main__":
    mcp.run()
