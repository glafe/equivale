import argparse
import json
import sqlite3
from pathlib import Path

from nutriguia import db as bd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MENUS_DIR = DATA_DIR / "Json-outputs-sin-notas"

# Nombres reales y objetivos diarios NO viven en este archivo (repo público) -- viven en
# data/personas_y_objetivos.json (gitignored, ver CLAUDE.md nota de privacidad y SETUP.md para
# cómo conseguirlo). Formato esperado: {"vigente_desde": "...", "personas": [{"persona": ...,
# "equivalentes_diarios": [...]}, ...]}.
PERSONAS_Y_OBJETIVOS_PATH = DATA_DIR / "personas_y_objetivos.json"


def _normalizar_grupo(grupo: str) -> str:
    # Ver CLAUDE.md: dos archivos originalmente usaban "Legumin" en vez de "Leguminosa".
    return "Leguminosa" if grupo == "Legumin" else grupo


def importar_catalogo(conn: sqlite3.Connection) -> int:
    catalogo = json.loads((MENUS_DIR / "catalogo-alimentos.json").read_text(encoding="utf-8"))
    n = 0
    for grupo, entradas in catalogo["grupos"].items():
        grupo = _normalizar_grupo(grupo)
        for entrada in entradas:
            doc = {
                "alimento": entrada["alimento"],
                "grupo": grupo,
                "cantidad_por_equivalente": entrada["cantidad_por_equivalente"],
            }
            if entrada.get("asuncion"):
                doc["asuncion"] = True
            bd.guardar_alimento(conn, doc)
            n += 1
    return n


def importar_recetas(conn: sqlite3.Connection, force: bool = False) -> int:
    # `recetas` se edita en vivo desde el Editor de recetas (views/editor_recetas.py) desde
    # 2026-08-24 -- esas ediciones solo viven en la base de datos, NO en recetas.json.
    # Re-importar sin --force las borraría. Ver ARCHITECTURE.md.
    existentes = bd.contar_recetas(conn)
    if not force and existentes > 0:
        print("  (recetas ya tiene datos -- se omite, usar --force-recetas para sobreescribir)")
        return existentes
    banco = json.loads((DATA_DIR / "recetas.json").read_text(encoding="utf-8"))
    for doc in banco["recetas"]:
        bd.guardar_receta(conn, doc)
    return len(banco["recetas"])


def importar_personas_y_objetivos(conn: sqlite3.Connection) -> tuple[int, int]:
    if not PERSONAS_Y_OBJETIVOS_PATH.exists():
        print(
            f"  ({PERSONAS_Y_OBJETIVOS_PATH.name} no encontrado -- se omite personas/objetivos, "
            "ver SETUP.md para conseguirlo)"
        )
        return len(bd.listar_personas(conn)), sum(
            1 for p in bd.listar_personas(conn) if bd.obtener_objetivo(conn, p)
        )

    contenido = json.loads(PERSONAS_Y_OBJETIVOS_PATH.read_text(encoding="utf-8"))
    vigente_desde = contenido["vigente_desde"]
    for p in contenido["personas"]:
        bd.crear_persona(conn, p["persona"])
        bd.guardar_objetivo(conn, p["persona"], vigente_desde, p["equivalentes_diarios"])
    return len(contenido["personas"]), len(contenido["personas"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-recetas", action="store_true",
        help="Sobreescribir la tabla recetas aunque ya tenga datos (borra ediciones hechas "
             "desde el Editor de recetas -- usar con cuidado).",
    )
    args = parser.parse_args()

    conn = bd.get_conn()
    n_catalogo = importar_catalogo(conn)
    n_recetas = importar_recetas(conn, force=args.force_recetas)
    n_personas, n_objetivos = importar_personas_y_objetivos(conn)

    print("Import completo:")
    print(f"  catalogo_alimentos: {n_catalogo}")
    print(f"  recetas:            {n_recetas}")
    print(f"  personas:           {n_personas}")
    print(f"  objetivos:          {n_objetivos}")


if __name__ == "__main__":
    main()
