"""nutriguia/html_semanal.py no toca Mongo -- estas pruebas usan datos sintéticos (nombres/valores
inventados, no reales de ninguna persona) para poder correr en cualquier clon del repo."""

from nutriguia.html_semanal import generar_html_semanal

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


def _es_html_valido(contenido: str) -> bool:
    return contenido.startswith("<!DOCTYPE html") and "</html>" in contenido


def test_genera_html_con_semana_mixta():
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={"AOA": 15, "Cereal": 10, "Verdura": 5, "Fruta": 4},
        asignacion=ASIGNACION_MIXTA,
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_html_valido(pagina)
    assert "Menú 1" in pagina
    assert "Aplica: Lunes, Martes, Viernes" in pagina
    assert len(pagina) > 1000


def test_genera_html_con_semana_completamente_libre():
    asignacion = {dia: None for dia in ASIGNACION_MIXTA}
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion=asignacion,
        menus_por_nombre={},
        catalogo={},
    )
    assert _es_html_valido(pagina)
    assert "todavía no tiene ningún día guardado con nombre" in pagina


def test_genera_html_sin_objetivo_no_truena():
    """Una persona sin objetivo diario configurado (ver FR-001/Personas) no debe romper el HTML --
    solo se omite la sección de objetivo."""
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "Menú 1", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_html_valido(pagina)
    assert "Objetivo diario" not in pagina


def test_menu_sin_dia_asignado_no_truena():
    """Un menú guardado con nombre pero que todavía no se asignó a ningún día de la semana debe
    seguir apareciendo en el HTML (como referencia), solo sin la etiqueta "Aplica: ..."."""
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={d: None for d in ASIGNACION_MIXTA},
        menus_por_nombre={"Menú 1": MENU_EJEMPLO},
        catalogo=CATALOGO_EJEMPLO,
    )
    assert _es_html_valido(pagina)
    assert "Sin día asignado en Menú semanal todavía" in pagina


def test_ingrediente_sin_catalogo_usa_fallback_de_equivalentes():
    """"Fruta libre" no está en CATALOGO_EJEMPLO -- no debe tronar, debe caer al fallback
    "N equiv." (ver _cantidad_real())."""
    from nutriguia.cantidades import cantidad_real

    assert cantidad_real("Fruta libre", 1, CATALOGO_EJEMPLO) == "1 equiv."
    assert cantidad_real("Avena en hojuelas", 2, CATALOGO_EJEMPLO) == "1/2 taza"


def test_ingrediente_libre_no_imprime_none():
    """Un ingrediente sin grupo_smae (alimento libre, ej. especias) NO debe imprimir "None 0"."""
    from nutriguia.html_semanal import _chip_grupo_html

    chip = _chip_grupo_html(None, 0)
    assert "Libre" in chip
    assert "None" not in chip

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
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "Con libre", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"Con libre": menu_con_libre},
        catalogo={},
    )
    assert _es_html_valido(pagina)
    assert "None" not in pagina


def _receta(nombre: str, n_ingredientes: int = 1) -> dict:
    return {
        "nombre": nombre,
        "ingredientes": [
            {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 1, "incluido": True}
            for _ in range(n_ingredientes)
        ],
    }


def test_tiempo_par_va_a_grid_de_dos_columnas():
    """Dos recetas en el mismo tiempo -- ninguna debe marcarse `receta-completa` (el CSS Grid ya
    las acomoda lado a lado sin necesitar que alguna ocupe el ancho completo)."""
    from nutriguia.html_semanal import _tiempo_html

    bloque = _tiempo_html("desayuno", [_receta("A"), _receta("B")], {})
    assert bloque.count('class="receta"') == 2
    assert "receta-completa" not in bloque


def test_tiempo_impar_ultimo_a_ancho_completo():
    """Con un número impar de recetas, la última se marca `receta-completa` (ocupa las 2 columnas
    del grid) en vez de dejar un hueco vacío al lado."""
    from nutriguia.html_semanal import _tiempo_html

    bloque = _tiempo_html("desayuno", [_receta("A"), _receta("B"), _receta("C")], {})
    assert bloque.count("receta-completa") == 1
    # La última (C) es la que queda a ancho completo, no A ni B.
    assert '<div class="receta receta-completa"><p class="receta-nombre">C</p>' in bloque


def test_html_escapa_nombres_con_caracteres_especiales():
    """Nombres de menú/receta/ingrediente se insertan escapados -- un nombre con `<`/`>`/`&` no
    debe alterar la estructura del HTML generado (defensivo; estos nombres los pone el propio
    usuario en Mongo, no una fuente externa, pero no cuesta nada evitar el riesgo)."""
    menu_travieso = {
        "actual_diario": {},
        "tiempos": {
            "desayuno": {
                "seleccion": [
                    {
                        "nombre": "<b>Receta</b> & cía",
                        "ingredientes": [
                            {"alimento": "<i>Alimento</i>", "grupo_smae": "AOA", "equivalentes": 1, "incluido": True},
                        ],
                    }
                ]
            }
        },
    }
    pagina = generar_html_semanal(
        persona="<script>alert(1)</script>",
        objetivo_diario={},
        asignacion={"lunes": "Travieso", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"Travieso": menu_travieso},
        catalogo={},
    )
    assert _es_html_valido(pagina)
    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina


def test_html_con_recetas_pareadas_no_truena():
    menu = {
        "actual_diario": {"AOA": 3},
        "tiempos": {"desayuno": {"seleccion": [_receta("A"), _receta("B"), _receta("C")]}},
    }
    pagina = generar_html_semanal(
        persona="Persona de prueba",
        objetivo_diario={},
        asignacion={"lunes": "M", **{d: None for d in list(ASIGNACION_MIXTA)[1:]}},
        menus_por_nombre={"M": menu},
        catalogo={},
    )
    assert _es_html_valido(pagina)
