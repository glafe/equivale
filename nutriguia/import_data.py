import argparse
import json
from pathlib import Path

from pymongo.database import Database

from nutriguia.db import get_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MENUS_DIR = DATA_DIR / "Json-outputs-sin-notas"

GRUPOS_CANONICOS = [
    "AOA",
    "Cereal",
    "Verdura",
    "Fruta",
    "Aceite s/p",
    "Aceite c/p",
    "Leguminosa",
]

# Nombres reales y objetivos diarios NO viven en este archivo (repo público) -- viven en
# data/personas_y_objetivos.json (gitignored, ver CLAUDE.md nota de privacidad y SETUP.md para
# cómo conseguirlo). Formato esperado: {"vigente_desde": "...", "personas": [{"persona": ...,
# "equivalentes_diarios": [...]}, ...]}.
PERSONAS_Y_OBJETIVOS_PATH = DATA_DIR / "personas_y_objetivos.json"


def _normalizar_grupo(grupo: str) -> str:
    # Ver CLAUDE.md: dos archivos originalmente usaban "Legumin" en vez de "Leguminosa".
    return "Leguminosa" if grupo == "Legumin" else grupo


def importar_catalogo(db: Database) -> int:
    catalogo = json.loads((MENUS_DIR / "catalogo-alimentos.json").read_text(encoding="utf-8"))
    docs = []
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
            docs.append(doc)
    db.catalogo_alimentos.delete_many({})
    db.catalogo_alimentos.insert_many(docs)
    db.catalogo_alimentos.create_index("alimento", unique=True)
    return len(docs)


def importar_menus(db: Database) -> int:
    archivos = sorted(p for p in MENUS_DIR.glob("*.json") if p.name != "catalogo-alimentos.json")
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in archivos]
    db.menus.delete_many({})
    db.menus.insert_many(docs)
    db.menus.create_index([("persona", 1), ("periodo", 1)], unique=True)
    return len(docs)


def importar_recetas(db: Database, force: bool = False) -> int:
    # `recetas` se edita en vivo desde el Editor de recetas (views/editor_recetas.py) desde
    # 2026-08-24 -- esas ediciones solo viven en Mongo, NO en recetas.json. Re-importar sin
    # --force las borraría. Ver ARCHITECTURE.md.
    if not force and db.recetas.count_documents({}) > 0:
        print("  (recetas ya tiene datos -- se omite, usar --force-recetas para sobreescribir)")
        return db.recetas.count_documents({})
    banco = json.loads((DATA_DIR / "recetas.json").read_text(encoding="utf-8"))
    docs = banco["recetas"]
    db.recetas.delete_many({})
    db.recetas.insert_many(docs)
    db.recetas.create_index("tiempo_tipico")
    for grupo in GRUPOS_CANONICOS:
        db.recetas.create_index(f"vector_equivalentes.{grupo}")
    return len(docs)


def importar_personas_y_objetivos(db: Database) -> tuple[int, int]:
    if not PERSONAS_Y_OBJETIVOS_PATH.exists():
        print(
            f"  ({PERSONAS_Y_OBJETIVOS_PATH.name} no encontrado -- se omite personas/objetivos, "
            "ver SETUP.md para conseguirlo)"
        )
        return db.personas.count_documents({}), db.objetivos.count_documents({})

    contenido = json.loads(PERSONAS_Y_OBJETIVOS_PATH.read_text(encoding="utf-8"))
    vigente_desde = contenido["vigente_desde"]
    personas_docs = [{"persona": p["persona"]} for p in contenido["personas"]]
    objetivos_docs = [
        {
            "persona": p["persona"],
            "vigente_desde": vigente_desde,
            "equivalentes_diarios": p["equivalentes_diarios"],
        }
        for p in contenido["personas"]
    ]

    db.personas.delete_many({})
    db.personas.insert_many(personas_docs)
    db.objetivos.delete_many({})
    db.objetivos.insert_many(objetivos_docs)
    return len(personas_docs), len(objetivos_docs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-recetas", action="store_true",
        help="Sobreescribir la colección recetas aunque ya tenga datos (borra ediciones hechas "
             "desde el Editor de recetas -- usar con cuidado).",
    )
    args = parser.parse_args()

    db = get_db()
    n_catalogo = importar_catalogo(db)
    n_menus = importar_menus(db)
    n_recetas = importar_recetas(db, force=args.force_recetas)
    n_personas, n_objetivos = importar_personas_y_objetivos(db)

    print("Import completo:")
    print(f"  catalogo_alimentos: {n_catalogo}")
    print(f"  menus:              {n_menus}")
    print(f"  recetas:            {n_recetas}")
    print(f"  personas:           {n_personas}")
    print(f"  objetivos:          {n_objetivos}")


if __name__ == "__main__":
    main()
