"""Acceso a SQLite (reemplaza MongoDB desde 2026-09-04 -- ver BUGS.md KC-002: MongoDB 8.x sigue
roto en kernels Linux >=6.19 por un bug de TCMalloc/rseq sin fecha de fix, y el objetivo de
distribuir EquiVale como app instalable en Windows/Linux hace que depender de un servicio de base
de datos aparte sea la fricción equivocada). SQLite es un archivo único, sin servicio, sin
instalación aparte -- viene en la librería estándar de Python.

Cada tabla tiene columnas reales solo para lo que se usa como clave/filtro, más una columna
`datos` con el resto del documento serializado como JSON -- `nutriguia/validation.py` ya son
funciones puras que reciben/devuelven esos dicts anidados tal cual, así que no hay que normalizar
a tablas relacionales (habría que reconstruir los dicts desde filas de todas formas, sin ganar
nada: no hay reportes ni queries analíticas que se beneficien de normalizar).

En vez de un shim genérico tipo Mongo (`find`/`$set` interpretados a mano -- su propia fuente de
bugs), este módulo expone funciones nombradas por caso de uso real, mismo estilo que
`validation.py`/`chequeos.py`/`cantidades.py`. Todas reciben la conexión como primer argumento
(no hay estado global aquí) -- eso las vuelve triviales de probar con `sqlite3.connect(":memory:")`.

No contiene lógica de negocio -- eso vive en `nutriguia/validation.py`.
"""

import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS personas (
  persona TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS objetivos (
  persona TEXT PRIMARY KEY REFERENCES personas(persona),
  vigente_desde TEXT NOT NULL,
  datos TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalogo_alimentos (
  alimento TEXT PRIMARY KEY,
  grupo TEXT,
  cantidad_por_equivalente TEXT NOT NULL,
  asuncion INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recetas (
  receta_id TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  datos TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS menus_construidos (
  persona TEXT NOT NULL,
  fecha TEXT NOT NULL,
  nombre TEXT,
  datos TEXT NOT NULL,
  PRIMARY KEY (persona, fecha)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dia_nombre ON menus_construidos(persona, nombre)
  WHERE nombre IS NOT NULL;

CREATE TABLE IF NOT EXISTS asignacion_semanal (
  persona TEXT PRIMARY KEY,
  datos TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS duplicados_descartados (
  a TEXT NOT NULL,
  b TEXT NOT NULL,
  PRIMARY KEY (a, b)
);
"""


def get_path() -> str:
    return os.environ.get("SQLITE_PATH", "data/equivale.db")


def inicializar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_ESQUEMA)
    conn.commit()


def get_conn() -> sqlite3.Connection:
    path = get_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    inicializar_schema(conn)
    return conn


# ---------------------------------------------------------------- personas -

def listar_personas(conn: sqlite3.Connection) -> list[str]:
    filas = conn.execute("SELECT persona FROM personas ORDER BY persona").fetchall()
    return [f["persona"] for f in filas]


def existe_persona(conn: sqlite3.Connection, persona: str) -> bool:
    fila = conn.execute("SELECT 1 FROM personas WHERE persona = ?", (persona,)).fetchone()
    return fila is not None


def crear_persona(conn: sqlite3.Connection, persona: str) -> None:
    conn.execute("INSERT OR IGNORE INTO personas (persona) VALUES (?)", (persona,))
    conn.commit()


def eliminar_persona(conn: sqlite3.Connection, persona: str) -> None:
    conn.execute("DELETE FROM objetivos WHERE persona = ?", (persona,))
    conn.execute("DELETE FROM personas WHERE persona = ?", (persona,))
    conn.commit()


# --------------------------------------------------------------- objetivos -

def obtener_objetivo(conn: sqlite3.Connection, persona: str) -> dict | None:
    fila = conn.execute(
        "SELECT vigente_desde, datos FROM objetivos WHERE persona = ?", (persona,)
    ).fetchone()
    if fila is None:
        return None
    doc = json.loads(fila["datos"])
    doc["persona"] = persona
    doc["vigente_desde"] = fila["vigente_desde"]
    return doc


def guardar_objetivo(
    conn: sqlite3.Connection, persona: str, vigente_desde: str, equivalentes_diarios: list
) -> None:
    """Reemplaza el objetivo vigente de `persona` -- una sola fila por persona (mismo
    comportamiento que el `delete_many` + `insert_one` de Mongo, ahora un upsert real)."""
    datos = json.dumps({"equivalentes_diarios": equivalentes_diarios})
    conn.execute(
        """INSERT INTO objetivos (persona, vigente_desde, datos) VALUES (?, ?, ?)
           ON CONFLICT(persona) DO UPDATE SET
               vigente_desde = excluded.vigente_desde, datos = excluded.datos""",
        (persona, vigente_desde, datos),
    )
    conn.commit()


# ---------------------------------------------------------- catalogo_alimentos -

def _alimento_de_fila(fila: sqlite3.Row) -> dict:
    doc = {
        "alimento": fila["alimento"],
        "grupo": fila["grupo"],
        "cantidad_por_equivalente": fila["cantidad_por_equivalente"],
    }
    if fila["asuncion"]:
        doc["asuncion"] = True
    return doc


def listar_catalogo(conn: sqlite3.Connection) -> list[dict]:
    filas = conn.execute(
        "SELECT alimento, grupo, cantidad_por_equivalente, asuncion FROM catalogo_alimentos"
    ).fetchall()
    return [_alimento_de_fila(f) for f in filas]


def obtener_alimento(conn: sqlite3.Connection, alimento: str) -> dict | None:
    fila = conn.execute(
        "SELECT alimento, grupo, cantidad_por_equivalente, asuncion "
        "FROM catalogo_alimentos WHERE alimento = ?",
        (alimento,),
    ).fetchone()
    return _alimento_de_fila(fila) if fila else None


def guardar_alimento(conn: sqlite3.Connection, documento: dict) -> None:
    conn.execute(
        """INSERT INTO catalogo_alimentos (alimento, grupo, cantidad_por_equivalente, asuncion)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(alimento) DO UPDATE SET
               grupo = excluded.grupo,
               cantidad_por_equivalente = excluded.cantidad_por_equivalente,
               asuncion = excluded.asuncion""",
        (
            documento["alimento"],
            documento.get("grupo"),
            documento["cantidad_por_equivalente"],
            1 if documento.get("asuncion") else 0,
        ),
    )
    conn.commit()


def eliminar_alimento(conn: sqlite3.Connection, alimento: str) -> None:
    conn.execute("DELETE FROM catalogo_alimentos WHERE alimento = ?", (alimento,))
    conn.commit()


# --------------------------------------------------------------------- recetas -

def _receta_de_fila(fila: sqlite3.Row) -> dict:
    doc = json.loads(fila["datos"])
    doc["receta_id"] = fila["receta_id"]
    doc["nombre"] = fila["nombre"]
    return doc


def listar_recetas(conn: sqlite3.Connection, tiempo: str | None = None) -> list[dict]:
    """`tiempo` filtra por pertenencia a `tiempo_tipico` (lista) -- equivalente al filtro Mongo
    `{"tiempo_tipico": tiempo}`, que hace match si `tiempo` está DENTRO del array. A esta escala
    (86 recetas) cargar todo y filtrar en Python es más simple que mantener una tabla auxiliar."""
    filas = conn.execute("SELECT receta_id, nombre, datos FROM recetas").fetchall()
    recetas = [_receta_de_fila(f) for f in filas]
    if tiempo:
        recetas = [r for r in recetas if tiempo in r.get("tiempo_tipico", [])]
    return recetas


def obtener_receta(conn: sqlite3.Connection, receta_id: str) -> dict | None:
    fila = conn.execute(
        "SELECT receta_id, nombre, datos FROM recetas WHERE receta_id = ?", (receta_id,)
    ).fetchone()
    return _receta_de_fila(fila) if fila else None


def guardar_receta(conn: sqlite3.Connection, documento: dict) -> None:
    resto = {k: v for k, v in documento.items() if k not in ("receta_id", "nombre")}
    conn.execute(
        """INSERT INTO recetas (receta_id, nombre, datos) VALUES (?, ?, ?)
           ON CONFLICT(receta_id) DO UPDATE SET nombre = excluded.nombre, datos = excluded.datos""",
        (documento["receta_id"], documento["nombre"], json.dumps(resto)),
    )
    conn.commit()


def eliminar_receta(conn: sqlite3.Connection, receta_id: str) -> None:
    conn.execute("DELETE FROM recetas WHERE receta_id = ?", (receta_id,))
    conn.commit()


def buscar_recetas_con_ingrediente(conn: sqlite3.Connection, alimento: str) -> list[dict]:
    """Equivalente al filtro Mongo `{"ingredientes.alimento": alimento}` -- cargar todo y filtrar
    en Python, mismo patrón que ya usa `chequeos.py` para todo lo demás."""
    return [
        r for r in listar_recetas(conn)
        if any(ing["alimento"] == alimento for ing in r["ingredientes"])
    ]


def contar_recetas(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM recetas").fetchone()["n"]


# ------------------------------------------------------------ menus_construidos -

def _dia_de_fila(fila: sqlite3.Row) -> dict:
    doc = json.loads(fila["datos"])
    doc["persona"] = fila["persona"]
    doc["fecha"] = fila["fecha"]
    doc["nombre"] = fila["nombre"]
    return doc


def obtener_dia(conn: sqlite3.Connection, persona: str, fecha: str) -> dict | None:
    fila = conn.execute(
        "SELECT persona, fecha, nombre, datos FROM menus_construidos "
        "WHERE persona = ? AND fecha = ?",
        (persona, fecha),
    ).fetchone()
    return _dia_de_fila(fila) if fila else None


def listar_dias(conn: sqlite3.Connection, persona: str) -> list[dict]:
    filas = conn.execute(
        "SELECT persona, fecha, nombre, datos FROM menus_construidos "
        "WHERE persona = ? ORDER BY fecha DESC",
        (persona,),
    ).fetchall()
    return [_dia_de_fila(f) for f in filas]


def listar_todos_los_dias(conn: sqlite3.Connection) -> list[dict]:
    filas = conn.execute("SELECT persona, fecha, nombre, datos FROM menus_construidos").fetchall()
    return [_dia_de_fila(f) for f in filas]


def buscar_dias_con_ingrediente(conn: sqlite3.Connection, alimento: str) -> list[tuple]:
    """[(documento, tiempo, indice, instancia, ingrediente), ...] -- mismo resultado que la query
    Mongo por dot-notation `{"ingredientes.alimento": alimento}` sobre `menus_construidos`, hecho
    en Python sobre el documento completo (mismo patrón que `chequeos.py`)."""
    resultado = []
    for doc in listar_todos_los_dias(conn):
        for tiempo, datos_tiempo in doc.get("tiempos", {}).items():
            for indice, inst in enumerate(datos_tiempo.get("seleccion", [])):
                for ing in inst["ingredientes"]:
                    if ing["alimento"] == alimento:
                        resultado.append((doc, tiempo, indice, inst, ing))
    return resultado


def guardar_dia(
    conn: sqlite3.Connection, persona: str, fecha: str, nombre: str | None, documento: dict
) -> None:
    resto = {k: v for k, v in documento.items() if k not in ("persona", "fecha", "nombre")}
    conn.execute(
        """INSERT INTO menus_construidos (persona, fecha, nombre, datos) VALUES (?, ?, ?, ?)
           ON CONFLICT(persona, fecha) DO UPDATE SET
               nombre = excluded.nombre, datos = excluded.datos""",
        (persona, fecha, nombre, json.dumps(resto)),
    )
    conn.commit()


def eliminar_dia(conn: sqlite3.Connection, persona: str, fecha: str) -> None:
    conn.execute(
        "DELETE FROM menus_construidos WHERE persona = ? AND fecha = ?", (persona, fecha)
    )
    conn.commit()


def nombre_en_uso(
    conn: sqlite3.Connection, persona: str, nombre: str, excluir_fecha: str | None = None
) -> bool:
    if excluir_fecha is not None:
        fila = conn.execute(
            "SELECT 1 FROM menus_construidos WHERE persona = ? AND nombre = ? AND fecha != ?",
            (persona, nombre, excluir_fecha),
        ).fetchone()
    else:
        fila = conn.execute(
            "SELECT 1 FROM menus_construidos WHERE persona = ? AND nombre = ?",
            (persona, nombre),
        ).fetchone()
    return fila is not None


# ------------------------------------------------------------ asignacion_semanal -

def obtener_asignacion(conn: sqlite3.Connection, persona: str) -> dict | None:
    fila = conn.execute(
        "SELECT persona, datos FROM asignacion_semanal WHERE persona = ?", (persona,)
    ).fetchone()
    if fila is None:
        return None
    doc = json.loads(fila["datos"])
    doc["persona"] = fila["persona"]
    return doc


def listar_todas_las_asignaciones(conn: sqlite3.Connection) -> list[dict]:
    filas = conn.execute("SELECT persona, datos FROM asignacion_semanal").fetchall()
    docs = []
    for f in filas:
        doc = json.loads(f["datos"])
        doc["persona"] = f["persona"]
        docs.append(doc)
    return docs


def guardar_asignacion(conn: sqlite3.Connection, persona: str, dias: dict) -> None:
    datos = json.dumps({"dias": dias})
    conn.execute(
        """INSERT INTO asignacion_semanal (persona, datos) VALUES (?, ?)
           ON CONFLICT(persona) DO UPDATE SET datos = excluded.datos""",
        (persona, datos),
    )
    conn.commit()


# ---------------------------------------------------------- duplicados_descartados -

def listar_pares_descartados(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    filas = conn.execute("SELECT a, b FROM duplicados_descartados").fetchall()
    return {(f["a"], f["b"]) for f in filas}


def descartar_par(conn: sqlite3.Connection, a: str, b: str) -> None:
    par = tuple(sorted((a, b)))
    conn.execute("INSERT OR IGNORE INTO duplicados_descartados (a, b) VALUES (?, ?)", par)
    conn.commit()


def deshacer_descarte(conn: sqlite3.Connection, a: str, b: str) -> None:
    par = tuple(sorted((a, b)))
    conn.execute("DELETE FROM duplicados_descartados WHERE a = ? AND b = ?", par)
    conn.commit()
