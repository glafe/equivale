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
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    None: "Libre",  # alimento libre (ej. especias, "al gusto") -- sin grupo SMAE, no cuenta EQ
}

_INK = colors.HexColor("#2B2621")
_MUTED = colors.HexColor("#6B6459")
_BORDE = colors.HexColor("#DAD3C4")
_FONDO_SUAVE = colors.HexColor("#F7F4EE")

_ESTILO_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15, leading=17, textColor=_INK)
_ESTILO_SUBTITULO = ParagraphStyle("subtitulo", fontName="Helvetica", fontSize=7.5, leading=9, textColor=_MUTED)
_ESTILO_MENU_NOMBRE = ParagraphStyle("menu_nombre", fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=_INK)
_ESTILO_MENU_DIAS = ParagraphStyle("menu_dias", fontName="Helvetica-Oblique", fontSize=8.5, leading=10, textColor=_MUTED)
_ESTILO_TIEMPO = ParagraphStyle("tiempo", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=colors.HexColor("#3C6E68"))
_ESTILO_RECETA = ParagraphStyle("receta", fontName="Helvetica-BoldOblique", fontSize=9, leading=11, textColor=_INK, spaceBefore=3)
_ESTILO_INGREDIENTE = ParagraphStyle("ingrediente", fontName="Helvetica", fontSize=8, leading=10, textColor=_INK)
_ESTILO_CANTIDAD = ParagraphStyle("cantidad", fontName="Helvetica", fontSize=8, leading=10, textColor=_INK)
_ESTILO_VACIO = ParagraphStyle("vacio", fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=_MUTED)
_ESTILO_NOTA = ParagraphStyle("nota", fontName="Helvetica", fontSize=8, leading=10, textColor=_MUTED)


def _chip_grupo_texto(grupo: str | None, eq: int) -> tuple[str, colors.Color, colors.Color]:
    """`grupo` es None para un alimento libre (ej. especias, "al gusto") dentro de una receta --
    sin esto, `f"{grupo} {eq}"` literalmente imprimía "None 0" en el PDF (detectado en QA en vivo
    contra datos reales, 2026-08-30). Ese caso no lleva el conteo de EQ (siempre 0, no aporta
    información) -- solo la etiqueta "Libre"."""
    color_fondo = GRUPO_COLOR.get(grupo, "#555555")
    texto = ETIQUETA_CORTA[None] if grupo is None else f"{ETIQUETA_CORTA.get(grupo, grupo)} {eq}"
    return texto, colors.HexColor(color_fondo), colors.HexColor(color_texto_legible(color_fondo))


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
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
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
    """Una fila por INGREDIENTE (a pedido del usuario, 2026-08-30 -- antes venían apilados varios
    por fila): Grupo | Cantidad | Alimento en columnas separadas, letra más chica para que quepan
    más filas por hoja. La celda de Grupo (chip de color con el EQ del grupo en esta receta) se
    fusiona verticalmente sobre todas las filas de ese grupo -- así se ve de un vistazo qué
    ingrediente(s) forman cada equivalente, igual que en `menu-Sep.xlsx`, sin repetir el chip."""
    ancho_grupo = 20 * mm
    ancho_cantidad = 24 * mm
    ancho_alimento = ancho_total - ancho_grupo - ancho_cantidad
    grupos = _agrupar_por_grupo(receta["ingredientes"])
    filas: list[list] = []
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (1, 0), (-1, -1), 8),
    ]
    if not grupos:
        return Table(
            [["", Paragraph("Sin ingredientes incluidos.", _ESTILO_VACIO)]],
            colWidths=[ancho_grupo, ancho_cantidad + ancho_alimento],
            style=TableStyle(estilo),
        )
    for grupo, eq, ings in grupos:
        texto_chip, color_fondo, color_texto = _chip_grupo_texto(grupo, eq)
        fila_inicio = len(filas)
        for ing in ings:
            cantidad = _cantidad_real(ing["alimento"], ing["equivalentes"], catalogo)
            nombre = ing["alimento"] + (" <i>(opcional)</i>" if ing.get("opcional") else "")
            filas.append([
                texto_chip if ing is ings[0] else "",
                Paragraph(cantidad, _ESTILO_CANTIDAD),
                Paragraph(nombre, _ESTILO_INGREDIENTE),
            ])
        fila_fin = len(filas) - 1
        if fila_fin > fila_inicio:
            estilo.append(("SPAN", (0, fila_inicio), (0, fila_fin)))
        estilo += [
            ("BACKGROUND", (0, fila_inicio), (0, fila_fin), color_fondo),
            ("TEXTCOLOR", (0, fila_inicio), (0, fila_fin), color_texto),
            ("FONTNAME", (0, fila_inicio), (0, fila_fin), "Helvetica-Bold"),
            ("FONTSIZE", (0, fila_inicio), (0, fila_fin), 7.5),
            ("ALIGN", (0, fila_inicio), (0, fila_fin), "CENTER"),
            ("VALIGN", (0, fila_inicio), (0, fila_fin), "MIDDLE"),
        ]
    tabla = Table(filas, colWidths=[ancho_grupo, ancho_cantidad, ancho_alimento])
    tabla.setStyle(TableStyle(estilo))
    return tabla


_GUTTER_COLUMNAS = 6 * mm


def _bloque_recetas(recetas: list[dict], catalogo: dict, ancho_util: float) -> list:
    """Las recetas de UN tiempo, en pares a dos columnas para aprovechar todo el ancho de la hoja
    (a pedido del usuario, 2026-08-30 -- antes se apilaban una debajo de otra dejando la mitad
    derecha de la página en blanco). Si el tiempo tiene un número impar de recetas, la última va
    sola a ancho completo en vez de dejar una columna vacía. Cada par se envuelve en
    `KeepTogether` para que las dos recetas de esa fila no se separen en un salto de página."""
    ancho_col = (ancho_util - _GUTTER_COLUMNAS) / 2
    flowables: list = []
    for i in range(0, len(recetas), 2):
        par = recetas[i : i + 2]
        if len(par) == 1:
            receta = par[0]
            flowables.append(
                KeepTogether([
                    Paragraph(receta["nombre"], _ESTILO_RECETA),
                    _tabla_receta(receta, catalogo, ancho_util),
                ])
            )
        else:
            celda_izq = [Paragraph(par[0]["nombre"], _ESTILO_RECETA), _tabla_receta(par[0], catalogo, ancho_col)]
            celda_der = [Paragraph(par[1]["nombre"], _ESTILO_RECETA), _tabla_receta(par[1], catalogo, ancho_col)]
            fila = Table([[celda_izq, celda_der]], colWidths=[ancho_col, ancho_col])
            fila.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("RIGHTPADDING", (0, 0), (0, 0), _GUTTER_COLUMNAS),
                        ("LEFTPADDING", (1, 0), (1, 0), 0),
                        ("RIGHTPADDING", (1, 0), (1, 0), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            flowables.append(KeepTogether([fila]))
        flowables.append(Spacer(1, 1.5 * mm))
    return flowables


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
    margen = 10 * mm
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
        Spacer(1, 2 * mm),
    ]
    if objetivo_diario:
        story.append(Paragraph("Objetivo diario", _ESTILO_TIEMPO))
        story.append(Spacer(1, 1 * mm))
        story.append(_chips_horizontales(objetivo_diario, ancho_util))
        story.append(Spacer(1, 3 * mm))

    nombres_ordenados = sorted(menus_por_nombre.keys())
    if not nombres_ordenados:
        story.append(Paragraph(f"{persona} todavía no tiene ningún día guardado con nombre.", _ESTILO_NOTA))

    # Sin PageBreak entre menús (a pedido del usuario, 2026-08-30, para no desperdiciar papel
    # cuando un menú es corto) -- fluyen uno tras otro y Reportlab solo salta de página cuando de
    # verdad no cabe más contenido. Cada receta (nombre + tabla) va en un KeepTogether para que no
    # se corte a la mitad justo en un salto de página.
    for idx, nombre in enumerate(nombres_ordenados):
        if idx > 0:
            story.append(Spacer(1, 3 * mm))
            story.append(HRFlowable(width="100%", thickness=0.75, color=_BORDE, spaceAfter=3 * mm))
        menu = menus_por_nombre[nombre]
        dias_aplica = dias_por_nombre.get(nombre)
        etiqueta_dias = (
            "Aplica: " + ", ".join(DIA_LABEL[d] for d in dias_aplica)
            if dias_aplica
            else "Sin día asignado en Menú semanal todavía"
        )
        story.append(Paragraph(nombre, _ESTILO_MENU_NOMBRE))
        story.append(Paragraph(etiqueta_dias, _ESTILO_MENU_DIAS))
        story.append(Spacer(1, 2 * mm))

        for tiempo in TIEMPOS:
            recetas = menu.get("tiempos", {}).get(tiempo, {}).get("seleccion", [])
            if not recetas:
                continue
            story.append(Paragraph(TIEMPO_LABEL[tiempo], _ESTILO_TIEMPO))
            story.extend(_bloque_recetas(recetas, catalogo, ancho_util))
            story.append(Spacer(1, 1 * mm))

        actual_diario = menu.get("actual_diario", {})
        if actual_diario:
            story.append(Paragraph("Total real de este menú", _ESTILO_TIEMPO))
            story.append(Spacer(1, 1 * mm))
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
