"""nutriguia/html_lista_super.py no toca Mongo -- estas pruebas usan datos sintéticos (nombres
inventados, no reales de ninguna persona) para poder correr en cualquier clon del repo."""

from nutriguia.html_lista_super import _agrupar_por_grupo, generar_html_lista_super

CATALOGO_EJEMPLO = {
    "Pollo": {"alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "30 g"},
    "Avena en hojuelas": {"alimento": "Avena en hojuelas", "grupo": "Cereal", "cantidad_por_equivalente": "1/4 taza"},
    "Manzana": {"alimento": "Manzana", "grupo": "Fruta", "cantidad_por_equivalente": "1 pieza"},
    "Canela en polvo": {"alimento": "Canela en polvo", "grupo": None, "cantidad_por_equivalente": "al gusto"},
    # "Fruta fantasma" deliberadamente NO está en el catálogo -- referencia huérfana.
}


def _es_html_valido(contenido: str) -> bool:
    return contenido.startswith("<!DOCTYPE html") and "</html>" in contenido


def test_genera_html_con_varios_grupos():
    pagina = generar_html_lista_super(
        personas=["Persona de prueba"],
        equivalentes_por_alimento={"Pollo": 12, "Avena en hojuelas": 4, "Manzana": 3},
        catalogo=CATALOGO_EJEMPLO,
        notas=[],
    )
    assert _es_html_valido(pagina)
    assert "Pollo" in pagina and "Avena en hojuelas" in pagina and "Manzana" in pagina
    assert "360 g" in pagina  # 12 equivalentes x 30 g


def test_consolida_titulo_con_varias_personas():
    pagina = generar_html_lista_super(
        personas=["A", "B"],
        equivalentes_por_alimento={"Pollo": 5},
        catalogo=CATALOGO_EJEMPLO,
        notas=[],
    )
    assert "A + B" in pagina


def test_sin_ingredientes_no_truena():
    pagina = generar_html_lista_super(
        personas=["Persona de prueba"], equivalentes_por_alimento={}, catalogo={}, notas=[]
    )
    assert _es_html_valido(pagina)
    assert "Sin ingredientes que comprar todavía" in pagina


def test_notas_se_incluyen_y_se_escapan():
    pagina = generar_html_lista_super(
        personas=["Persona de prueba"],
        equivalentes_por_alimento={"Pollo": 1},
        catalogo=CATALOGO_EJEMPLO,
        notas=["<script>alert(1)</script>"],
    )
    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina


def test_alimento_sin_catalogo_usa_fallback_y_va_a_sin_grupo():
    """"Fruta fantasma" no está en CATALOGO_EJEMPLO -- no debe tronar, cae al fallback "N equiv."
    y se agrupa como "Sin grupo / libre", no se pierde de la lista."""
    pagina = generar_html_lista_super(
        personas=["Persona de prueba"],
        equivalentes_por_alimento={"Fruta fantasma": 2},
        catalogo=CATALOGO_EJEMPLO,
        notas=[],
    )
    assert _es_html_valido(pagina)
    assert "Fruta fantasma" in pagina
    assert "2 equiv." in pagina
    assert "Sin grupo / libre" in pagina


def test_alimento_libre_grupo_none_no_imprime_none():
    pagina = generar_html_lista_super(
        personas=["Persona de prueba"],
        equivalentes_por_alimento={"Canela en polvo": 0},
        catalogo=CATALOGO_EJEMPLO,
        notas=[],
    )
    assert "Canela en polvo" in pagina
    assert ">None<" not in pagina


def test_agrupar_por_grupo_orden_fijo_no_alfabetico():
    """AOA antes que Cereal antes que Verdura... (ORDEN_GRUPOS), no alfabético ("AOA" < "Aceite"
    alfabéticamente pero el orden fijo pone AOA primero de todas formas -- aquí se prueba con
    Cereal antes que AOA en el dict de entrada para confirmar que el orden de salida no depende
    del orden de inserción ni del alfabético)."""
    grupos = _agrupar_por_grupo(
        {"Avena en hojuelas": 1, "Pollo": 1, "Manzana": 1}, CATALOGO_EJEMPLO
    )
    orden_obtenido = [g for g, _ in grupos]
    assert orden_obtenido == ["AOA", "Cereal", "Fruta"]


def test_agrupar_por_grupo_alfabetico_dentro_del_grupo():
    catalogo = dict(CATALOGO_EJEMPLO)
    catalogo["Zanahoria"] = {"alimento": "Zanahoria", "grupo": "Fruta", "cantidad_por_equivalente": "1 pieza"}
    grupos = _agrupar_por_grupo({"Zanahoria": 1, "Manzana": 1}, catalogo)
    fruta = next(items for g, items in grupos if g == "Fruta")
    assert [alimento for alimento, _ in fruta] == ["Manzana", "Zanahoria"]
