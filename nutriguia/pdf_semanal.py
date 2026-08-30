"""Generación del PDF de "Menú semanal" (2026-08-29, a pedido del usuario; **rediseñado por
completo el 2026-08-30** tras revisar cómo el usuario usaba de verdad `menu-Sep.xlsx` -- fuera de
git, ver nota de privacidad en `CLAUDE.md`).

La primera versión (0.12.0) era una cuadrícula de 7 días x 5 tiempos con solo el nombre de cada
receta -- el usuario aclaró que lo que de verdad necesitaba era otra cosa: poder identificar rápido
la relación entre el EQUIVALENTE y el INGREDIENTE real (cantidad + alimento), organizado por
**menú** (no por día), con una nota de a qué días de la semana aplica cada uno -- exactamente el
patrón de `menu-Sep.xlsx`: un bloque por menú ("Dan - Menu 1: Lunes, Miércoles, Viernes"), y dentro
de cada tiempo, por receta, una fila por grupo SMAE con su EQ y los ingredientes reales que lo
forman.

Sigue sin tocar Mongo -- recibe los datos ya resueltos (`asignacion`, `menus_por_nombre`,
`catalogo`) desde `views/menu_semanal.py`, mismo patrón que `nutriguia/validation.py`. Necesita
`catalogo` (a diferencia de la v1) porque ahora sí muestra la cantidad real de cada ingrediente
(`escalar_cantidad()` + `paso_equivalente()`, igual que `views/menu_del_dia.py`), no solo su conteo
de equivalentes.
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nutriguia.cantidades import escalar_cantidad
from nutriguia.colores import GRUPO_COLOR, color_texto_legible
from nutriguia.validation import paso_equivalente

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIA_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
TIEMPOS = ["al_despertar", "desayuno", "colacion", "comida", "cena"]
TIEMPO_LABEL = {
    "al_despertar": "Al despertar",
    "desayuno": "Desayuno",
    "colacion": "Colación",
    "comida": "Comida",
    "cena": "Cena",
}
# Versión corta de GRUPO_ETIQUETA (colores.py) -- en el PDF los chips comparten columna con hasta
# 6 más (fila de objetivo/total) o con el ancho fijo de la columna de grupo de cada receta, así
# que "Aceites s/proteína"/"Aceite c/proteína"/"Leguminosas" no caben y se recortan visualmente.
ETIQUETA_CORTA = {
    "Fruta": "Fruta",
    "Verdura": "Verdura",
    "Cereal": "Cereal",
    "Leguminosa": "Legumin.",
    "AOA": "AOA",
    "Aceite s/p": "Aceite s/p",
    "Aceite c/p": "Aceite c/p",
}

_INK = colors.HexColor("#2B2621")
_MUTED = colors.HexColor("#6B6459")
_BORDE = colors.HexColor("#DAD3C4")
_FONDO_SUAVE = colors.HexColor("#F7F4EE")

_ESTILO_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=_INK)
_ESTILO_SUBTITULO = ParagraphStyle("subtitulo", fontName="Helvetica", fontSize=10, leading=12, textColor=_MUTED)
_ESTILO_MENU_NOMBRE = ParagraphStyle("menu_nombre", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=_INK)
_ESTILO_MENU_DIAS = ParagraphStyle("menu_dias", fontName="Helvetica-Oblique", fontSize=11, leading=13, textColor=_MUTED)
_ESTILO_TIEMPO = ParagraphStyle("tiempo", fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=colors.HexColor("#3C6E68"))
_ESTILO_RECETA = ParagraphStyle("receta", fontName="Helvetica-BoldOblique", fontSize=11.5, leading=14, textColor=_INK, spaceBefore=4)
_ESTILO_INGREDIENTE = ParagraphStyle("ingrediente", fontName="Helvetica", fontSize=10, leading=13, textColor=_INK)
_ESTILO_VACIO = ParagraphStyle("vacio", fontName="Helvetica-Oblique", fontSize=9.5, leading=12, textColor=_MUTED)
_ESTILO_NOTA = ParagraphStyle("nota", fontName="Helvetica", fontSize=10, leading=13, textColor=_MUTED)


def _chip_grupo_texto(grupo: str, eq: int) -> tuple[str, colors.Color, colors.Color]:
    color_fondo = GRUPO_COLOR.get(grupo, "#555555")
    return f"{ETIQUETA_CORTA.get(grupo, grupo)} {eq}", colors.HexColor(color_fondo), colors.HexColor(
        color_texto_legible(color_fondo)
    )


def _chips_horizontales(vector: dict[str, int], ancho_total: float):
    """Fila de chips de color, un grupo por columna -- para "Objetivo diario" y "Total real" de
    cada menú. Mismo `GRUPO_COLOR` que el resto de la app, con `ETIQUETA_CORTA` en vez de
    `GRUPO_ETIQUETA` por espacio."""
    grupos = sorted(vector.items())
    if not grupos:
        return Paragraph("—", _ESTILO_VACIO)
    ancho_col = ancho_total / len(grupos)
    fila = [[f"{ETIQUETA_CORTA.get(g, g)} {c}" for g, c in grupos]]
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDE),
    ]
    for i, (grupo, _) in enumerate(grupos):
        color = GRUPO_COLOR.get(grupo, "#555555")
        estilo.append(("BACKGROUND", (i, 0), (i, 0), colors.HexColor(color)))
        estilo.append(("TEXTCOLOR", (i, 0), (i, 0), colors.HexColor(color_texto_legible(color))))
    tabla = Table(fila, colWidths=[ancho_col] * len(grupos))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _cantidad_real(alimento: str, equivalentes: int, catalogo: dict) -> str:
    paso = paso_equivalente(alimento, catalogo)
    if paso is None:
        return f"{equivalentes} equiv."
    return escalar_cantidad(paso, equivalentes)


def _agrupar_por_grupo(ingredientes: list[dict]) -> list[tuple[str, int, list[dict]]]:
    """[(grupo, eq_total_del_grupo_en_esta_receta, [ingredientes]), ...] -- en el orden en que
    cada grupo aparece por primera vez en la receta, no alfabético (mismo orden que ya tenía)."""
    orden: list[str] = []
    por_grupo: dict[str, list[dict]] = {}
    for ing in ingredientes:
        if not ing.get("incluido", True):
            continue
        grupo = ing["grupo_smae"]
        if grupo not in por_grupo:
            por_grupo[grupo] = []
            orden.append(grupo)
        por_grupo[grupo].append(ing)
    return [(g, sum(i["equivalentes"] for i in por_grupo[g]), por_grupo[g]) for g in orden]


def _tabla_receta(receta: dict, catalogo: dict, ancho_total: float) -> Table:
    """Una fila por grupo SMAE que toca esta receta: chip de color con el EQ a la izquierda,
    cantidad real + nombre de cada ingrediente de ese grupo a la derecha (uno por línea) -- así se
    ve de un vistazo qué ingrediente(s) forman cada equivalente, igual que en `menu-Sep.xlsx`."""
    ancho_grupo = 34 * mm
    ancho_ing = ancho_total - ancho_grupo
    grupos = _agrupar_por_grupo(receta["ingredientes"])
    filas = []
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if not grupos:
        filas.append(["", Paragraph("Sin ingredientes incluidos.", _ESTILO_VACIO)])
    for i, (grupo, eq, ings) in enumerate(grupos):
        texto_chip, color_fondo, color_texto = _chip_grupo_texto(grupo, eq)
        celda_grupo = Table([[texto_chip]], colWidths=[ancho_grupo])
        celda_grupo.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
                    ("TEXTCOLOR", (0, 0), (-1, -1), color_texto),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        texto_ings = "<br/>".join(
            f"{_cantidad_real(ing['alimento'], ing['equivalentes'], catalogo)} — {ing['alimento']}"
            + (" <i>(opcional)</i>" if ing.get("opcional") else "")
            for ing in ings
        )
        filas.append([celda_grupo, Paragraph(texto_ings, _ESTILO_INGREDIENTE)])
    tabla = Table(filas, colWidths=[ancho_grupo, ancho_ing])
    tabla.setStyle(TableStyle(estilo))
    return tabla


def generar_pdf_semanal(
    persona: str,
    objetivo_diario: dict[str, int],
    asignacion: dict[str, str | None],
    menus_por_nombre: dict[str, dict],
    catalogo: dict[str, dict],
) -> bytes:
    """`asignacion`: {dia: nombre|None} (ver `asignacion_semanal` en schema.md). `menus_por_nombre`:
    {nombre: documento de `menus_construidos`} -- ya filtrado a la persona y a los que tienen
    nombre (`views/menu_semanal.py` `_cargar_menus_nombrados()`). `catalogo`: `cargar_catalogo()`,
    para resolver la cantidad real de cada ingrediente. Un bloque por cada menú en
    `menus_por_nombre` (aunque no esté asignado a ningún día -- así el PDF también sirve como
    referencia completa del banco de menús con nombre de esta persona), en orden alfabético."""
    buffer = io.BytesIO()
    ancho_pagina, alto_pagina = letter
    margen = 16 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margen,
        rightMargin=margen,
        topMargin=margen,
        bottomMargin=margen,
        title=f"Menú semanal - {persona}",
    )
    ancho_util = ancho_pagina - 2 * margen

    dias_por_nombre: dict[str, list[str]] = {}
    for dia in DIAS:
        nombre = asignacion.get(dia)
        if nombre is not None:
            dias_por_nombre.setdefault(nombre, []).append(dia)
    dias_libres = [d for d in DIAS if asignacion.get(d) is None]
    dias_rotos = {d: n for d, n in asignacion.items() if n is not None and n not in menus_por_nombre}

    story: list = [
        Paragraph(f"Menú semanal — {persona}", _ESTILO_TITULO),
        Paragraph(f"Generado el {date.today().isoformat()} con EquiVale", _ESTILO_SUBTITULO),
        Spacer(1, 3 * mm),
    ]
    if objetivo_diario:
        story.append(Paragraph("Objetivo diario", _ESTILO_TIEMPO))
        story.append(Spacer(1, 1.5 * mm))
        story.append(_chips_horizontales(objetivo_diario, ancho_util))
        story.append(Spacer(1, 5 * mm))

    nombres_ordenados = sorted(menus_por_nombre.keys())
    if not nombres_ordenados:
        story.append(Paragraph(f"{persona} todavía no tiene ningún día guardado con nombre.", _ESTILO_NOTA))

    for idx, nombre in enumerate(nombres_ordenados):
        if idx > 0:
            story.append(PageBreak())
        menu = menus_por_nombre[nombre]
        dias_aplica = dias_por_nombre.get(nombre)
        etiqueta_dias = (
            "Aplica: " + ", ".join(DIA_LABEL[d] for d in dias_aplica)
            if dias_aplica
            else "Sin día asignado en Menú semanal todavía"
        )
        story.append(Paragraph(nombre, _ESTILO_MENU_NOMBRE))
        story.append(Paragraph(etiqueta_dias, _ESTILO_MENU_DIAS))
        story.append(Spacer(1, 3 * mm))

        for tiempo in TIEMPOS:
            recetas = menu.get("tiempos", {}).get(tiempo, {}).get("seleccion", [])
            if not recetas:
                continue
            story.append(Paragraph(TIEMPO_LABEL[tiempo], _ESTILO_TIEMPO))
            for receta in recetas:
                story.append(Paragraph(receta["nombre"], _ESTILO_RECETA))
                story.append(_tabla_receta(receta, catalogo, ancho_util))
                story.append(Spacer(1, 2.5 * mm))
            story.append(Spacer(1, 2 * mm))

        actual_diario = menu.get("actual_diario", {})
        if actual_diario:
            story.append(Paragraph("Total real de este menú", _ESTILO_TIEMPO))
            story.append(Spacer(1, 1.5 * mm))
            story.append(_chips_horizontales(actual_diario, ancho_util))

    notas = []
    if dias_libres:
        notas.append("Libres/descanso: " + ", ".join(DIA_LABEL[d] for d in dias_libres) + ".")
    if dias_rotos:
        detalle = ", ".join(f"{DIA_LABEL[d]} ('{n}' ya no existe)" for d, n in dias_rotos.items())
        notas.append("Referencias rotas en Menú semanal -- revisar en Configuración: " + detalle + ".")
    if notas:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(" ".join(notas), _ESTILO_NOTA))

    doc.build(story)
    return buffer.getvalue()
