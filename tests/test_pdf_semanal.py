"""nutriguia/pdf_semanal.py no toca Mongo -- estas pruebas usan datos sintéticos (nombres/valores
inventados, no reales de ninguna persona) para poder correr en cualquier clon del repo."""

from nutriguia.pdf_semanal import generar_pdf_semanal

CATALOGO_EJEMPLO = {
    "Avena en hojuelas": {"alimento": "Avena en hojuelas", "grupo": "Cereal", "cantidad_por_equivalente": "1/4 taza"},
    "Leche semi": {"alimento": "Leche semi", "grupo": "AOA", "cantidad_por_equivalente": "1 taza"},
    "Pollo": {"alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "30 g"},
    "Nopal": {"alimento": "Nopal", "grupo": "Verdura", "cantidad_por_equivalente": "1 taza"},
    # "Fruta libre" deliberadamente NO está en el catálogo -- para probar el fallback a "N equiv."
}

MENU_EJEMPLO = {
    "persona": "prueba",
    "fecha": "2026-08-31",
    "nombre": "Menú 1",
    "actual_diario": {"AOA": 9, "Cereal": 2, "Verdura": 2, "Fruta": 1},
    "tiempos": {
        "desayuno": {
            "seleccion": [
                {
                    "nombre": "Avena con leche",
                    "ingredientes": [
                        {"alimento": "Avena en hojuelas", "grupo_smae": "Cereal", "equivalentes": 2, "incluido": True},
                        {"alimento": "Leche semi", "grupo_smae": "AOA", "equivalentes": 1, "incluido": True},
                        {"alimento": "Fruta libre", "grupo_smae": "Fruta", "equivalentes": 1, "incluido": True},
                    ],
                }
            ]
        },
        "comida": {
            "seleccion": [
                {
                    "nombre": "Tacos de pollo con nopal",
                    "ingredientes": [
                        {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 4, "incluido": True},
                        {"alimento": "Nopal", "grupo_smae": "Verdura", "equivalentes": 2, "incluido": True},
                        {"alimento": "Salsa extra", "grupo_smae": "Verdura", "equivalentes": 1, "incluido": False},
                    ],
                }
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
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_pdf_valido(pdf)
    assert len(pdf) > 1000


def test_genera_pdf_con_semana_completamente_libre():
    asignacion = {dia: None for dia in ASIGNACION_MIXTA}
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion=asignacion,
        menus_por_nombre={},
        catalogo={},
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
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_pdf_valido(pdf)


def test_menu_sin_dia_asignado_no_truena():
    """Un menú guardado con nombre pero que todavía no se asignó a ningún día de la semana debe
    seguir apareciendo en el PDF (como referencia), solo sin la etiqueta "Aplica: ..."."""
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={d: None for d in ASIGNACION_MIXTA},
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_pdf_valido(pdf)


def test_ingrediente_sin_catalogo_usa_fallback_de_equivalentes():
    """"Fruta libre" no está en CATALOGO_EJEMPLO -- no debe tronar, debe caer al fallback
    "N equiv." (ver _cantidad_real())."""
    from nutriguia.pdf_semanal import _cantidad_real

    assert _cantidad_real("Fruta libre", 1, CATALOGO_EJEMPLO) == "1 equiv."
    assert _cantidad_real("Avena en hojuelas", 2, CATALOGO_EJEMPLO) == "1/2 taza"


def test_ingrediente_libre_no_imprime_none():
    """Un ingrediente sin grupo_smae (alimento libre, ej. especias) NO debe imprimir "None 0" --
    detectado en QA en vivo contra datos reales, 2026-08-30 (ver _chip_grupo_texto())."""
    from nutriguia.pdf_semanal import _chip_grupo_texto

    texto, _, _ = _chip_grupo_texto(None, 0)
    assert texto == "Libre"
    assert "None" not in texto

    menu_con_libre = {
        "actual_diario": {},
        "tiempos": {
            "desayuno": {
                "seleccion": [
                    {
                        "nombre": "Café",
                        "ingredientes": [
                            {"alimento": "Canela en polvo", "grupo_smae": None, "equivalentes": 0, "incluido": True},
                        ],
                    }
                ]
            }
        },
    }
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "Con libre", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"Con libre": menu_con_libre},
        catalogo={},
    )
    assert _es_pdf_valido(pdf)


def _receta(nombre: str, n_ingredientes: int = 1) -> dict:
    return {
        "nombre": nombre,
        "ingredientes": [
            {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 1, "incluido": True}
            for _ in range(n_ingredientes)
        ],
    }


def test_bloque_recetas_par_va_a_dos_columnas():
    """Dos recetas en el mismo tiempo -- a pedido del usuario, 2026-08-30, deben ir lado a lado
    (dos columnas) en vez de apiladas, para aprovechar el ancho completo de la hoja."""
    from nutriguia.pdf_semanal import _bloque_recetas

    flowables = _bloque_recetas([_receta("A"), _receta("B")], {}, 180)
    # 1 KeepTogether con la fila de 2 columnas + 1 Spacer -- no dos bloques por separado.
    assert len(flowables) == 2


def test_bloque_recetas_impar_dernier_a_ancho_completo():
    """Con un número impar de recetas, la última va sola a ancho completo (no una columna vacía)."""
    from nutriguia.pdf_semanal import _bloque_recetas

    flowables = _bloque_recetas([_receta("A"), _receta("B"), _receta("C")], {}, 180)
    # 1 par (KeepTogether + Spacer) + 1 receta sola (KeepTogether + Spacer) = 4 flowables.
    assert len(flowables) == 4


def test_pdf_con_recetas_pareadas_no_truena():
    menu = {
        "actual_diario": {"AOA": 3},
        "tiempos": {"desayuno": {"seleccion": [_receta("A"), _receta("B"), _receta("C")]}},
    }
    pdf = generar_pdf_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "M", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"M": menu},
        catalogo={},
    )
    assert _es_pdf_valido(pdf)
