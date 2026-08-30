"""Generación del HTML de "Menú semanal" (2026-08-30, reemplaza `nutriguia/pdf_semanal.py` a
pedido del usuario: prefiere que EquiVale genere el HTML y usar el "Imprimir a PDF" del propio
navegador -- eso le da control total de márgenes/escala/qué tanto cabe por hoja, algo que ir
ajustando a ciegas en ReportLab (ver `CHANGELOG.md` 0.12.0-0.16.0) no daba. Mismo contenido y
mismo diseño visual que esa versión (mismo `GRUPO_COLOR`, mismo agrupamiento por menú/tiempo,
mismas dos columnas por tiempo) -- solo cambia el motor de render: un `<table>` HTML con
`rowspan` nativo en vez de `reportlab.Table` + `SPAN`, y CSS Grid para las dos columnas en vez del
emparejado manual (`_bloque_recetas()` ya no existe -- el navegador decide el corte de página
solo, con `break-inside: avoid` marcando qué no debe partirse a la mitad).

Sigue sin tocar Mongo -- recibe los datos ya resueltos (`asignacion`, `menus_por_nombre`,
`catalogo`) desde `views/menu_semanal.py`, mismo patrón que `nutriguia/validation.py`.
"""

import html
from datetime import date

from nutriguia.cantidades import escalar_cantidad
from nutriguia.colores import GRUPO_COLOR, color_texto_legible
from nutriguia.validation import paso_equivalente

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIA_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
TIEMPOS = ["al_despertar", "desayuno", "colacion", "comida", "cena"]
# A diferencia del PDF con ReportLab (Helvetica no trae esos glifos y salían como cuadros negros),
# el HTML sí renderiza emoji bien en cualquier navegador -- se restauran los mismos íconos que usa
# el resto de la app.
TIEMPO_LABEL = {
    "al_despertar": "🌅 Al despertar",
    "desayuno": "🍳 Desayuno",
    "colacion": "🍎 Colación",
    "comida": "🍽️ Comida",
    "cena": "🌙 Cena",
}
# Versión corta de GRUPO_ETIQUETA (colores.py) -- en el chip de grupo de cada receta el ancho de
# columna es angosto, así que "Aceites s/proteína"/"Aceite c/proteína"/"Leguminosas" no caben.
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

_INK = "#2B2621"
_MUTED = "#6B6459"
_BORDE = "#DAD3C4"
_TEAL = "#3C6E68"


def _esc(valor) -> str:
    return html.escape(str(valor))


def _chip_grupo_html(grupo: str | None, eq: int) -> str:
    """`grupo` es None para un alimento libre (ej. especias, "al gusto") dentro de una receta --
    ese caso no lleva el conteo de EQ (siempre 0, no aporta información), solo la etiqueta
    "Libre" (mismo criterio que la versión ReportLab, ver CHANGELOG 0.14.0)."""
    color = GRUPO_COLOR.get(grupo, "#555555")
    color_texto = color_texto_legible(color)
    texto = ETIQUETA_CORTA[None] if grupo is None else f"{ETIQUETA_CORTA.get(grupo, grupo)} {eq}"
    return f'<span class="chip" style="background:{color};color:{color_texto};">{_esc(texto)}</span>'


def _chips_fila_html(vector: dict[str, int]) -> str:
    """Fila de chips de color, uno por grupo -- para "Objetivo diario" y "Total real" de cada
    menú."""
    if not vector:
        return '<p class="vacio">—</p>'
    chips = "".join(_chip_grupo_html(g, c) for g, c in sorted(vector.items()))
    return f'<div class="chips-fila">{chips}</div>'


def _cantidad_real(alimento: str, equivalentes: int, catalogo: dict) -> str:
    paso = paso_equivalente(alimento, catalogo)
    if paso is None:
        return f"{equivalentes} equiv."
    return escalar_cantidad(paso, equivalentes)


def _agrupar_por_grupo(ingredientes: list[dict]) -> list[tuple[str, int, list[dict]]]:
    """[(grupo, eq_total_del_grupo_en_esta_receta, [ingredientes]), ...] -- en el orden en que
    cada grupo aparece por primera vez en la receta, no alfabético."""
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


def _tabla_receta_html(receta: dict, catalogo: dict) -> str:
    """Una fila por INGREDIENTE: Grupo | Cantidad | Alimento en columnas separadas. La celda de
    Grupo (chip de color con el EQ del grupo en esta receta) usa `rowspan` nativo de HTML para
    fusionarse sobre todas las filas de ese grupo -- así se ve de un vistazo qué ingrediente(s)
    forman cada equivalente, sin repetir el chip (mismo resultado visual que el `SPAN` de
    ReportLab, sin tener que calcular rangos de fila a mano)."""
    grupos = _agrupar_por_grupo(receta["ingredientes"])
    if not grupos:
        return '<table class="tabla-receta"><tr><td class="vacio" colspan="3">Sin ingredientes incluidos.</td></tr></table>'
    filas = []
    for grupo, eq, ings in grupos:
        color = GRUPO_COLOR.get(grupo, "#555555")
        color_texto = color_texto_legible(color)
        texto_chip = ETIQUETA_CORTA[None] if grupo is None else f"{ETIQUETA_CORTA.get(grupo, grupo)} {eq}"
        n = len(ings)
        for i, ing in enumerate(ings):
            cantidad = _cantidad_real(ing["alimento"], ing["equivalentes"], catalogo)
            nombre = _esc(ing["alimento"]) + (" <i>(opcional)</i>" if ing.get("opcional") else "")
            celda_grupo = (
                f'<td class="celda-grupo" rowspan="{n}" style="background:{color};color:{color_texto};">'
                f"{_esc(texto_chip)}</td>"
                if i == 0
                else ""
            )
            filas.append(
                f"<tr>{celda_grupo}"
                f'<td class="celda-cantidad">{_esc(cantidad)}</td>'
                f'<td class="celda-alimento">{nombre}</td></tr>'
            )
    return '<table class="tabla-receta">' + "".join(filas) + "</table>"


def _receta_html(receta: dict, catalogo: dict) -> str:
    return (
        '<div class="receta">'
        f'<p class="receta-nombre">{_esc(receta["nombre"])}</p>'
        f"{_tabla_receta_html(receta, catalogo)}"
        "</div>"
    )


def _tiempo_html(tiempo: str, recetas: list[dict], catalogo: dict) -> str:
    """Grid de 2 columnas (CSS, no manual como `_bloque_recetas()` de la versión ReportLab) para
    aprovechar todo el ancho de la hoja. Con un número impar de recetas, la última se marca
    `receta-completa` para que ocupe las dos columnas en vez de dejar un hueco vacío al lado."""
    tarjetas = [_receta_html(r, catalogo) for r in recetas]
    if len(tarjetas) % 2 == 1:
        tarjetas[-1] = tarjetas[-1].replace('class="receta"', 'class="receta receta-completa"', 1)
    return (
        f'<h3 class="tiempo">{_esc(TIEMPO_LABEL[tiempo])}</h3>'
        '<div class="recetas-grid">' + "".join(tarjetas) + "</div>"
    )


_CSS = f"""
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  padding: 10mm;
  background: #FBF9F4;
  color: {_INK};
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 10.5pt;
  line-height: 1.35;
}}
header {{ margin-bottom: 4mm; }}
h1 {{ font-size: 17pt; margin: 0 0 1mm; }}
.subtitulo {{ font-size: 8.5pt; color: {_MUTED}; margin: 0; }}
.aviso-pantalla {{
  margin: 3mm 0 0;
  padding: 2mm 3mm;
  background: #EFE9DA;
  border: 0.75pt solid {_BORDE};
  border-radius: 6px;
  font-size: 8.5pt;
  color: {_INK};
  display: inline-block;
}}
.tiempo {{ font-size: 11.5pt; color: {_TEAL}; margin: 3mm 0 1.5mm; }}
.menu-bloque {{ margin-bottom: 5mm; padding-top: 3mm; border-top: 0.75pt solid {_BORDE}; }}
.menu-bloque:first-of-type {{ border-top: none; padding-top: 0; }}
.menu-nombre {{ font-size: 14pt; margin: 0; }}
.menu-dias {{ font-size: 9pt; font-style: italic; color: {_MUTED}; margin: 0.5mm 0 2mm; }}
.recetas-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3mm 6mm;
  align-items: start;
}}
.receta {{ break-inside: avoid; page-break-inside: avoid; margin-bottom: 2mm; }}
.receta-completa {{ grid-column: 1 / -1; }}
.receta-nombre {{ font-size: 10pt; font-weight: 700; font-style: italic; margin: 0 0 1mm; }}
table.tabla-receta {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
table.tabla-receta td {{
  border: 0.5pt solid {_BORDE};
  padding: 1mm 1.5mm;
  vertical-align: top;
}}
.celda-grupo {{
  width: 19mm;
  text-align: center;
  vertical-align: middle;
  font-weight: 700;
  font-size: 8pt;
}}
.celda-cantidad {{ width: 22mm; white-space: nowrap; }}
.chips-fila {{ display: flex; flex-wrap: wrap; gap: 1.5mm; margin: 0 0 2mm; }}
.chip {{ padding: 0.8mm 2.2mm; border-radius: 999px; font-size: 8pt; font-weight: 700; }}
.vacio, .nota {{ color: {_MUTED}; font-size: 8.5pt; font-style: italic; }}
.nota {{ margin-top: 4mm; }}
@media print {{
  body {{ background: #fff; padding: 0; }}
  .solo-pantalla {{ display: none; }}
}}
@page {{ size: letter; margin: 10mm; }}
"""


def generar_html_semanal(
    persona: str,
    objetivo_diario: dict[str, int],
    asignacion: dict[str, str | None],
    menus_por_nombre: dict[str, dict],
    catalogo: dict[str, dict],
) -> str:
    """`asignacion`: {dia: nombre|None} (ver `asignacion_semanal` en schema.md). `menus_por_nombre`:
    {nombre: documento de `menus_construidos`} -- ya filtrado a la persona y a los que tienen
    nombre (`views/menu_semanal.py` `_cargar_menus_nombrados()`). `catalogo`: `cargar_catalogo()`,
    para resolver la cantidad real de cada ingrediente. Devuelve un documento HTML completo y
    autocontenido (CSS embebido, sin dependencias externas) -- se descarga como `.html` y el
    usuario lo abre en su navegador para imprimirlo o guardarlo como PDF (Ctrl/Cmd+P) con el
    control de márgenes/escala que le dé su propio navegador. Un bloque por cada menú en
    `menus_por_nombre` (aunque no esté asignado a ningún día -- así también sirve como referencia
    completa del banco de menús con nombre de esta persona), en orden alfabético."""
    dias_por_nombre: dict[str, list[str]] = {}
    for dia in DIAS:
        nombre = asignacion.get(dia)
        if nombre is not None:
            dias_por_nombre.setdefault(nombre, []).append(dia)
    dias_libres = [d for d in DIAS if asignacion.get(d) is None]
    dias_rotos = {d: n for d, n in asignacion.items() if n is not None and n not in menus_por_nombre}

    nombres_ordenados = sorted(menus_por_nombre.keys())
    bloques_menu: list[str] = []
    if not nombres_ordenados:
        bloques_menu.append(f'<p class="nota">{_esc(persona)} todavía no tiene ningún día guardado con nombre.</p>')

    for nombre in nombres_ordenados:
        menu = menus_por_nombre[nombre]
        dias_aplica = dias_por_nombre.get(nombre)
        etiqueta_dias = (
            "Aplica: " + ", ".join(DIA_LABEL[d] for d in dias_aplica)
            if dias_aplica
            else "Sin día asignado en Menú semanal todavía"
        )
        secciones_tiempo = []
        for tiempo in TIEMPOS:
            recetas = menu.get("tiempos", {}).get(tiempo, {}).get("seleccion", [])
            if recetas:
                secciones_tiempo.append(_tiempo_html(tiempo, recetas, catalogo))

        actual_diario = menu.get("actual_diario", {})
        total_html = (
            f'<h3 class="tiempo">Total real de este menú</h3>{_chips_fila_html(actual_diario)}'
            if actual_diario
            else ""
        )
        bloques_menu.append(
            '<section class="menu-bloque">'
            f'<h2 class="menu-nombre">{_esc(nombre)}</h2>'
            f'<p class="menu-dias">{_esc(etiqueta_dias)}</p>'
            + "".join(secciones_tiempo)
            + total_html
            + "</section>"
        )

    notas = []
    if dias_libres:
        notas.append("Libres/descanso: " + ", ".join(DIA_LABEL[d] for d in dias_libres) + ".")
    if dias_rotos:
        detalle = ", ".join(f"{DIA_LABEL[d]} ('{_esc(n)}' ya no existe)" for d, n in dias_rotos.items())
        notas.append("Referencias rotas en Menú semanal -- revisar en Configuración: " + detalle + ".")
    notas_html = f'<p class="nota">{" ".join(notas)}</p>' if notas else ""

    objetivo_html = (
        f'<h2 class="tiempo">Objetivo diario</h2>{_chips_fila_html(objetivo_diario)}' if objetivo_diario else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Menú semanal — {_esc(persona)}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>Menú semanal — {_esc(persona)}</h1>
  <p class="subtitulo">Generado el {date.today().isoformat()} con EquiVale.</p>
  <p class="aviso-pantalla solo-pantalla">💡 Usa Ctrl/Cmd+P para imprimir esta página o guardarla como PDF.</p>
</header>
{objetivo_html}
{"".join(bloques_menu)}
{notas_html}
</body>
</html>"""
