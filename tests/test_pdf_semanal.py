"""nutriguia/pdf_semanal.py no toca Mongo -- estas pruebas usan datos sintéticos (nombres/valores
inventados, no reales de ninguna persona) para poder correr en cualquier clon del repo."""

from nutriguia.pdf_semanal import generar_pdf_semanal

MENU_EJEMPLO = {
    "persona": "prueba",
    "fecha": "2026-08-31",
    "nombre": "Menú 1",
    "actual_diario": {"AOA": 15, "Cereal": 10, "Verdura": 5, "Fruta": 4},
    "tiempos": {
        "desayuno": {"seleccion": [{"nombre": "Avena remojada", "ingredientes": []}]},
        "comida": {
            "seleccion": [
                {"nombre": "Tacos de pollo", "ingredientes": []},
                {"nombre": "Ensalada de nopal", "ingredientes": []},
            ]
        },
        # "cena" deliberadamente ausente -- un tiempo que el usuario no llegó a armar.
    },
}

ASIGNACION_MIXTA = {
    "lunes": "Menú 1",
    "martes": "Menú 1",
    "miercoles": "Menú fantasma",  # referencia rota -- ya no existe en menus_por_nombre
    "jueves": None,  # libre / descanso
    "viernes": "Menú 1",
    "sabado": None,
    "domingo": None,
}


def _es_pdf_valido(contenido: bytes) -> bool:
    return contenido.startswith(b"%PDF-")


def test_genera_pdf_con_semana_mixta():
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={"AOA": 15, "Cereal": 10, "Verdura": 5, "Fruta": 4},
        asignacion=ASIGNACION_MIXTA,
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
    )
    assert _es_pdf_valido(pdf)
    assert len(pdf) > 1000


def test_genera_pdf_con_semana_completamente_libre():
    asignacion = {dia: None for dia in ASIGNACION_MIXTA}
    pdf = generar_pdf_semanal(
        persona="Persona de prueba", objetivo_diario={}, asignacion=asignacion, menus_por_nombre={}
    )
    assert _es_pdf_valido(pdf)


def test_genera_pdf_sin_objetivo_no_truena():
    """Una persona sin objetivo diario configurado (ver FR-001/Personas) no debe romper el PDF --
    solo se omite la fila de objetivo."""
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "Menú 1", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
    )
    assert _es_pdf_valido(pdf)
