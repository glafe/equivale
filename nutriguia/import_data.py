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

# Objetivos diarios confirmados con el usuario el 2026-08-24 para el periodo Ago-Sep 2026.
# Dan: equivalentes_diarios_indicados de Junio26-Dany.json.
# Pau: no existe equivalentes_diarios_indicados en ningún archivo 2026 de Pau -> se usa
# equivalentes_diarios del menu_id 1 de PauJunio26.json (decisión explícita del usuario).
# Ver schema.md -> "objetivos" para la nota de diseño (objetivo diario, no por tiempo).
VIGENTE_DESDE = "2026-08-24"
OBJETIVOS_CONFIRMADOS = [
    {
        "persona": "Dan",
        "vigente_desde": VIGENTE_DESDE,
        "equivalentes_diarios": [
            {"grupo": "AOA", "cantidad": 15},
            {"grupo": "Cereal", "cantidad": 10},
            {"grupo": "Verdura", "cantidad": 5},
            {"grupo": "Fruta", "cantidad": 4},
            {"grupo": "Aceite s/p", "cantidad": 3},
            {"grupo": "Aceite c/p", "cantidad": 1},
        ],
    },
    {
        "persona": "Pau",
        "vigente_desde": VIGENTE_DESDE,
        "equivalentes_diarios": [
            {"grupo": "AOA", "cantidad": 13},
            {"grupo": "Cereal", "cantidad": 6},
            {"grupo": "Leguminosa", "cantidad": 1},
            {"grupo": "Verdura", "cantidad": 5},
            {"grupo": "Aceite c/p", "cantidad": 1},
            {"grupo": "Aceite s/p", "cantidad": 3},
            {"grupo": "Fruta", "cantidad": 3},
        ],
    },
]


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


def importar_personas(db: Database) -> int:
    docs = [{"persona": "Dan"}, {"persona": "Pau"}]
    db.personas.delete_many({})
    db.personas.insert_many(docs)
    return len(docs)


def importar_objetivos(db: Database) -> int:
    db.objetivos.delete_many({})
    db.objetivos.insert_many(OBJETIVOS_CONFIRMADOS)
    return len(OBJETIVOS_CONFIRMADOS)


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
    n_personas = importar_personas(db)
    n_objetivos = importar_objetivos(db)

    print("Import completo:")
    print(f"  catalogo_alimentos: {n_catalogo}")
    print(f"  menus:              {n_menus}")
    print(f"  recetas:            {n_recetas}")
    print(f"  personas:           {n_personas}")
    print(f"  objetivos:          {n_objetivos}")


if __name__ == "__main__":
    main()
