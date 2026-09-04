"""Tests de nutriguia/db.py contra SQLite en memoria -- la capa de persistencia no tenía
cobertura antes de la migración de Mongo a SQLite (no había forma de probarla sin un Mongo vivo);
con SQLite se vuelve trivial."""

import sqlite3

import pytest

from nutriguia import db


@pytest.fixture
def conn():
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys=ON")
    db.inicializar_schema(conexion)
    yield conexion
    conexion.close()


def test_personas_crear_listar_eliminar(conn):
    db.crear_persona(conn, "Dan")
    db.crear_persona(conn, "Pau")
    db.crear_persona(conn, "Dan")  # duplicado, no debe romper (INSERT OR IGNORE)
    assert db.listar_personas(conn) == ["Dan", "Pau"]
    assert db.existe_persona(conn, "Dan")
    assert not db.existe_persona(conn, "Nadie")
    db.eliminar_persona(conn, "Dan")
    assert db.listar_personas(conn) == ["Pau"]


def test_objetivo_guardar_y_reemplazar(conn):
    db.crear_persona(conn, "Dan")
    assert db.obtener_objetivo(conn, "Dan") is None
    db.guardar_objetivo(conn, "Dan", "2026-08-24", [{"grupo": "AOA", "cantidad": 5}])
    obj = db.obtener_objetivo(conn, "Dan")
    assert obj["vigente_desde"] == "2026-08-24"
    assert obj["equivalentes_diarios"] == [{"grupo": "AOA", "cantidad": 5}]

    # una sola fila por persona -- guardar de nuevo reemplaza, no acumula historial
    db.guardar_objetivo(conn, "Dan", "2026-09-01", [{"grupo": "AOA", "cantidad": 6}])
    obj2 = db.obtener_objetivo(conn, "Dan")
    assert obj2["vigente_desde"] == "2026-09-01"
    assert obj2["equivalentes_diarios"] == [{"grupo": "AOA", "cantidad": 6}]


def test_catalogo_alimentos_upsert_y_asuncion(conn):
    db.guardar_alimento(conn, {"alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "30 g"})
    assert db.obtener_alimento(conn, "Pollo") == {
        "alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "30 g"
    }

    # grupo null (alimento libre) se preserva tal cual, no como string "None"
    db.guardar_alimento(conn, {"alimento": "Canela", "grupo": None, "cantidad_por_equivalente": "al gusto"})
    assert db.obtener_alimento(conn, "Canela")["grupo"] is None

    # asuncion solo aparece si es True, igual que en Mongo (campo disperso)
    db.guardar_alimento(conn, {
        "alimento": "Tofu", "grupo": "AOA", "cantidad_por_equivalente": "1/2 taza", "asuncion": True
    })
    assert db.obtener_alimento(conn, "Tofu")["asuncion"] is True
    assert "asuncion" not in db.obtener_alimento(conn, "Pollo")

    # upsert: re-guardar el mismo alimento actualiza en vez de duplicar
    db.guardar_alimento(conn, {"alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "40 g"})
    assert len(db.listar_catalogo(conn)) == 3
    assert db.obtener_alimento(conn, "Pollo")["cantidad_por_equivalente"] == "40 g"

    db.eliminar_alimento(conn, "Canela")
    assert db.obtener_alimento(conn, "Canela") is None


def test_recetas_listar_filtrar_por_tiempo_y_buscar_ingrediente(conn):
    db.guardar_receta(conn, {
        "receta_id": "avena-1", "nombre": "Avena",
        "tiempo_tipico": ["desayuno", "al_despertar"],
        "ingredientes": [{"alimento": "Avena en hojuelas", "grupo_smae": "Cereal", "equivalentes": 1}],
        "vector_equivalentes": {"Cereal": 1},
    })
    db.guardar_receta(conn, {
        "receta_id": "ensalada-1", "nombre": "Ensalada",
        "tiempo_tipico": ["comida"],
        "ingredientes": [{"alimento": "Lechuga", "grupo_smae": "Verdura", "equivalentes": 2}],
        "vector_equivalentes": {"Verdura": 2},
    })

    assert db.contar_recetas(conn) == 2
    todas = {r["nombre"] for r in db.listar_recetas(conn)}
    assert todas == {"Avena", "Ensalada"}

    solo_desayuno = db.listar_recetas(conn, tiempo="desayuno")
    assert [r["nombre"] for r in solo_desayuno] == ["Avena"]

    encontradas = db.buscar_recetas_con_ingrediente(conn, "Lechuga")
    assert [r["nombre"] for r in encontradas] == ["Ensalada"]
    assert db.buscar_recetas_con_ingrediente(conn, "Zanahoria") == []

    receta = db.obtener_receta(conn, "avena-1")
    assert receta["ingredientes"][0]["alimento"] == "Avena en hojuelas"

    db.eliminar_receta(conn, "avena-1")
    assert db.obtener_receta(conn, "avena-1") is None
    assert db.contar_recetas(conn) == 1


def test_menus_construidos_guardar_obtener_listar_y_nombre_unico(conn):
    documento = {
        "estado": "completo",
        "objetivo_diario": {"AOA": 5},
        "actual_diario": {"AOA": 5},
        "delta_diario": {"AOA": 0},
        "tiempos": {
            "comida": {
                "seleccion": [
                    {
                        "receta_id": "pasta-1",
                        "nombre": "Pasta con res",
                        "ingredientes": [
                            {"alimento": "Pasta cocida", "grupo_smae": "Cereal", "equivalentes": 3}
                        ],
                    }
                ],
                "actual": {"Cereal": 3},
            }
        },
    }
    db.guardar_dia(conn, "Dan", "2026-09-01", "Semana 1", documento)

    dia = db.obtener_dia(conn, "Dan", "2026-09-01")
    assert dia["estado"] == "completo"
    assert dia["nombre"] == "Semana 1"
    assert dia["tiempos"]["comida"]["seleccion"][0]["nombre"] == "Pasta con res"

    assert db.obtener_dia(conn, "Dan", "2026-09-02") is None
    assert [d["fecha"] for d in db.listar_dias(conn, "Dan")] == ["2026-09-01"]
    assert len(db.listar_todos_los_dias(conn)) == 1

    encontrados = db.buscar_dias_con_ingrediente(conn, "Pasta cocida")
    assert len(encontrados) == 1
    doc, tiempo, indice, inst, ing = encontrados[0]
    assert tiempo == "comida" and indice == 0 and ing["equivalentes"] == 3

    # nombre único por persona -- otra fecha con el mismo nombre debe fallar
    with pytest.raises(sqlite3.IntegrityError):
        db.guardar_dia(conn, "Dan", "2026-09-08", "Semana 1", documento)

    assert db.nombre_en_uso(conn, "Dan", "Semana 1")
    assert not db.nombre_en_uso(conn, "Dan", "Semana 1", excluir_fecha="2026-09-01")
    assert not db.nombre_en_uso(conn, "Dan", "Semana Fantasma")

    # otra persona SÍ puede reusar el mismo nombre (unicidad es por persona)
    db.guardar_dia(conn, "Pau", "2026-09-01", "Semana 1", documento)
    assert db.obtener_dia(conn, "Pau", "2026-09-01")["nombre"] == "Semana 1"

    db.eliminar_dia(conn, "Dan", "2026-09-01")
    assert db.obtener_dia(conn, "Dan", "2026-09-01") is None


def test_asignacion_semanal(conn):
    assert db.obtener_asignacion(conn, "Dan") is None
    dias = {"lunes": "Semana 1", "martes": None}
    db.guardar_asignacion(conn, "Dan", dias)
    asignacion = db.obtener_asignacion(conn, "Dan")
    assert asignacion["dias"] == dias

    db.guardar_asignacion(conn, "Dan", {"lunes": None, "martes": "Semana 1"})
    assert db.obtener_asignacion(conn, "Dan")["dias"]["martes"] == "Semana 1"

    assert len(db.listar_todas_las_asignaciones(conn)) == 1


def test_duplicados_descartados_orden_y_deshacer(conn):
    db.descartar_par(conn, "Yogurt", "Yogur")
    # orden inverso de argumentos debe seguir contando como el mismo par (normalizado alfabético)
    db.descartar_par(conn, "Yogur", "Yogurt")
    pares = db.listar_pares_descartados(conn)
    assert pares == {("Yogur", "Yogurt")}

    db.deshacer_descarte(conn, "Yogurt", "Yogur")
    assert db.listar_pares_descartados(conn) == set()
