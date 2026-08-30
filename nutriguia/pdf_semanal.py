"""Generación del PDF de "Menú semanal" (2026-08-29, a pedido del usuario) -- pensado para
imprimir y pegar en la cocina, reemplazando el uso que se le daba antes a un Excel manual
(`menu-Sep.xlsx` y similares, fuera de git -- ver nota de privacidad en `CLAUDE.md`): letra grande
para leerse de lejos, orientación horizontal para que quepan los 7 días, y los mismos colores
estandarizados por grupo SMAE que ya usa el resto de la app (`GRUPO_COLOR` en `colores.py`) en vez
de inventar una paleta nueva para el PDF.

No toca Mongo -- recibe los datos ya resueltos (`asignacion`, `menus_por_nombre`) desde
`views/menu_semanal.py`, igual que `nutriguia/validation.py` no toca Mongo. Así se puede probar
con datos sintéticos sin levantar una base real (ver `tests/test_pdf_semanal.py`).

Solo recetas por nombre, sin ingredientes ni steppers -- el detalle completo se sigue viendo en
"Menú del día"; este PDF es un recordatorio visual rápido, no un reemplazo de la app.
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from nutriguia.colores import GRUPO_COLOR, GRUPO_ETIQUETA, color_texto_legible

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
LIBRE_TEXTO = "Libre / descanso"

_INK = colors.HexColor("#2B2621")
_MUTED = colors.HexColor("#6B6459")
_BORDE = colors.HexColor("#DAD3C4")
_FONDO_ENCABEZADO = colors.HexColor("#F7F4EE")
_FONDO_LIBRE = colors.HexColor("#EFEAE0")
_ROJO_ROTO = colors.HexColor("#B23A2E")

_ESTILO_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=_INK)
_ESTILO_SUBTITULO = ParagraphStyle("subtitulo", fontName="Helvetica", fontSize=10, leading=12, textColor=_MUTED)
_ESTILO_DIA = ParagraphStyle("dia", fontName="Helvetica-Bold", fontSize=15, leading=17, alignment=1, textColor=_INK)
_ESTILO_TIEMPO = ParagraphStyle("tiempo", fontName="Helvetica-Bold", fontSize=11.5, leading=13, textColor=_INK)
_ESTILO_RECETA = ParagraphStyle("receta", fontName="Helvetica-Bold", fontSize=12.5, leading=14.5, textColor=_INK)
_ESTILO_VACIO = ParagraphStyle("vacio", fontName="Helvetica", fontSize=11, leading=13, textColor=_MUTED, alignment=1)
_ESTILO_LIBRE = ParagraphStyle("libre", fontName="Helvetica-Oblique", fontSize=13, leading=15, textColor=_MUTED, alignment=1)
_ESTILO_ROTO = ParagraphStyle("roto", fontName="Helvetica-Oblique", fontSize=11, leading=13, textColor=_ROJO_ROTO, alignment=1)


def _tabla_chips(vector: dict[str, int], ancho: float) -> Table | Paragraph:
    """Mini-tabla de una columna, una fila por grupo presente en `vector`, cada una con el mismo
    color de fondo que usa el resto de la app para ese grupo (`GRUPO_COLOR`) -- el "color
    estandarizado" que pidió el usuario, no una paleta inventada para el PDF."""
    grupos = sorted(vector.items())
    if not grupos:
        return Paragraph("—", _ESTILO_VACIO)
    filas = [[f"{GRUPO_ETIQUETA.get(g, g)} {c}"] for g, c in grupos]
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDE),
    ]
    for i, (grupo, _) in enumerate(grupos):
        color = GRUPO_COLOR.get(grupo, "#555555")
        estilo.append(("BACKGROUND", (0, i), (0, i), colors.HexColor(color)))
        estilo.append(("TEXTCOLOR", (0, i), (0, i), colors.HexColor(color_texto_legible(color))))
    tabla = Table(filas, colWidths=[ancho])
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _chips_horizontales(vector: dict[str, int], ancho_total: float) -> Table | Paragraph:
    """Como `_tabla_chips`, pero en una sola fila (un grupo por columna) en vez de apilados -- para
    el resumen de "Objetivo diario" en la parte de arriba del PDF, donde sí hay ancho de sobra y
    apilar los 7 grupos verticalmente solo desperdiciaría alto de página."""
    grupos = sorted(vector.items())
    if not grupos:
        return Paragraph("—", _ESTILO_VACIO)
    ancho_col = ancho_total / len(grupos)
    fila = [[f"{GRUPO_ETIQUETA.get(g, g)} {c}" for g, c in grupos]]
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


def _celda_dia_libre_o_roto(nombre: str | None) -> Paragraph | None:
    """None = el día sí tiene un menú válido (seguir con las recetas normales). Si no, regresa el
    Paragraph a mostrar (spaneado sobre las 5 filas de tiempo)."""
    if nombre is None:
        return Paragraph(LIBRE_TEXTO, _ESTILO_LIBRE)
    # Sin emoji: las fuentes base de reportlab (Helvetica) no traen esos glifos y salen como
    # cuadros negros en el PDF -- a diferencia de la app en Streamlit, donde sí se ven bien.
    return Paragraph(f"'{nombre}' ya no existe", _ESTILO_ROTO)


def generar_pdf_semanal(
    persona: str,
    objetivo_diario: dict[str, int],
    asignacion: dict[str, str | None],
    menus_por_nombre: dict[str, dict],
) -> bytes:
    """`asignacion`: {dia: nombre|None} (ver `asignacion_semanal` en schema.md). `menus_por_nombre`:
    {nombre: documento de `menus_construidos`} -- ya filtrado a la persona y a los que tienen
    nombre, tal como lo carga `views/menu_semanal.py` `_cargar_menus_nombrados()`. Un nombre
    asignado que ya no está en `menus_por_nombre` se dibuja como referencia rota, mismo criterio
    de "detectar, no arreglar solo" que usa Configuración -- no es trabajo de este módulo decidir
    qué hacer con eso."""
    buffer = io.BytesIO()
    ancho_pagina, alto_pagina = landscape(letter)
    margen = 9 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=margen,
        rightMargin=margen,
        topMargin=margen,
        bottomMargin=margen,
        title=f"Menú semanal - {persona}",
    )

    story: list = [
        Paragraph(f"Menú semanal — {persona}", _ESTILO_TITULO),
        Paragraph(f"Generado el {date.today().isoformat()} con EquiVale", _ESTILO_SUBTITULO),
        Spacer(1, 3 * mm),
    ]

    ancho_util = ancho_pagina - 2 * margen
    ancho_label = 30 * mm
    ancho_dia = (ancho_util - ancho_label) / 7
    col_widths = [ancho_label] + [ancho_dia] * 7

    if objetivo_diario:
        fila_objetivo = [Paragraph("Objetivo diario", _ESTILO_TIEMPO)]
        chips = _chips_horizontales(objetivo_diario, ancho_util - ancho_label)
        fila_objetivo.append(chips)
        tabla_objetivo = Table([fila_objetivo], colWidths=[ancho_label, ancho_util - ancho_label])
        tabla_objetivo.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.6, _BORDE),
                    ("BACKGROUND", (0, 0), (0, 0), _FONDO_ENCABEZADO),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tabla_objetivo)
        story.append(Spacer(1, 2 * mm))

    # --- Encabezado: nombre de cada día + qué menú tiene asignado (o "Libre") ---
    encabezado = [""]
    for dia in DIAS:
        nombre = asignacion.get(dia)
        if nombre and nombre in menus_por_nombre:
            sub = nombre
        elif nombre:
            sub = "no disponible"
        else:
            sub = "Libre"
        encabezado.append(Paragraph(f"{DIA_LABEL[dia]}<br/><font size=8 color='#6B6459'>{sub}</font>", _ESTILO_DIA))
    datos = [encabezado]

    # --- Una fila por tiempo, con las recetas de cada día (o vacío si ese tiempo no se usó) ---
    for i, tiempo in enumerate(TIEMPOS):
        fila = [Paragraph(TIEMPO_LABEL[tiempo], _ESTILO_TIEMPO)]
        for dia in DIAS:
            nombre = asignacion.get(dia)
            valido = nombre is not None and nombre in menus_por_nombre
            if not valido:
                # Solo la primera fila de tiempo lleva el contenido -- el resto queda vacío
                # porque esa columna se fusiona verticalmente (ver SPAN más abajo).
                fila.append(_celda_dia_libre_o_roto(nombre) if i == 0 else "")
                continue
            seleccion = menus_por_nombre[nombre].get("tiempos", {}).get(tiempo, {}).get("seleccion", [])
            if not seleccion:
                fila.append(Paragraph("–", _ESTILO_VACIO))
            else:
                texto = "<br/>".join(r["nombre"] for r in seleccion)
                fila.append(Paragraph(texto, _ESTILO_RECETA))
        datos.append(fila)

    # --- Resumen: equivalentes reales del día completo, con los chips de color por grupo ---
    fila_resumen = [Paragraph("Total del<br/>día", _ESTILO_TIEMPO)]
    for dia in DIAS:
        nombre = asignacion.get(dia)
        if nombre and nombre in menus_por_nombre:
            fila_resumen.append(_tabla_chips(menus_por_nombre[nombre].get("actual_diario", {}), ancho_dia - 8))
        else:
            fila_resumen.append("")
    datos.append(fila_resumen)

    tabla = Table(datos, colWidths=col_widths, repeatRows=1)
    estilos = [
        ("GRID", (0, 0), (-1, -1), 0.6, _BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -2), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), _FONDO_ENCABEZADO),
        ("BACKGROUND", (0, 1), (0, -1), _FONDO_ENCABEZADO),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for idx, dia in enumerate(DIAS):
        col = idx + 1
        nombre = asignacion.get(dia)
        valido = nombre is not None and nombre in menus_por_nombre
        if not valido:
            estilos.append(("SPAN", (col, 1), (col, len(TIEMPOS))))
            estilos.append(("VALIGN", (col, 1), (col, len(TIEMPOS)), "MIDDLE"))
            estilos.append(("BACKGROUND", (col, 1), (col, len(TIEMPOS)), _FONDO_LIBRE))
    tabla.setStyle(TableStyle(estilos))
    story.append(tabla)

    doc.build(story)
    return buffer.getvalue()
