"""Generación del HTML de "Lista del súper" (FR-004, 2026-08-30, a pedido del usuario) --
mismo patrón que `nutriguia/html_semanal.py`: un documento HTML autocontenido (CSS embebido, sin
dependencias externas) que el usuario abre en su navegador y usa Ctrl/Cmd+P para imprimir o
guardar como PDF, con la identidad visual "Barro" de siempre.

Sigue sin tocar Mongo -- recibe los datos ya resueltos (`personas`, `equivalentes_por_alimento`,
`catalogo`, `notas`) desde `views/lista_super.py`, mismo patrón que `nutriguia/validation.py`.
"""

import html
from datetime import date

from nutriguia.cantidades import cantidad_real
from nutriguia.colores import COLOR_POR_DEFECTO, GRUPO_COLOR, GRUPO_ETIQUETA, color_texto_legible

# Orden de aparición fijo (no alfabético) -- mismo criterio en toda la app (ver colores.py).
ORDEN_GRUPOS = ["AOA", "Cereal", "Verdura", "Fruta", "Aceite s/p", "Aceite c/p", "Leguminosa"]

_INK = "#2B2621"
_MUTED = "#6B6459"
_BORDE = "#DAD3C4"
_TEAL = "#3C6E68"


def _esc(valor) -> str:
    return html.escape(str(valor))


def agrupar_alimentos_por_grupo(
    equivalentes_por_alimento: dict[str, int], catalogo: dict
) -> list[tuple[str | None, list[tuple[str, int]]]]:
    """[(grupo, [(alimento, equivalentes), ...]), ...] -- grupo resuelto desde
    `catalogo[alimento]["grupo"]` (no desde un `grupo_smae` de ingrediente, que ya no se conserva
    tras sumar por alimento). `None` = libre (ej. especias) o alimento ya no está en el catálogo
    (referencia huérfana) -- ambos casos se agrupan como "Sin grupo / libre" al final. Orden fijo
    de grupos (`ORDEN_GRUPOS`), alfabético dentro de cada uno. Un alimento con un `grupo` que no es
    ninguno de los 7 canónicos (no debería pasar según `schema.md`, pero si el catálogo llegara a
    tener un dato sucio) igual aparece -- en su propia sección al final, alfabético por nombre de
    grupo -- en vez de perderse silenciosamente de la lista de compras."""
    por_grupo: dict[str | None, list[tuple[str, int]]] = {}
    for alimento, equivalentes in equivalentes_por_alimento.items():
        grupo = catalogo.get(alimento, {}).get("grupo")
        por_grupo.setdefault(grupo, []).append((alimento, equivalentes))

    resultado = []
    for grupo in ORDEN_GRUPOS:
        if grupo in por_grupo:
            resultado.append((grupo, sorted(por_grupo[grupo])))
    grupos_no_canonicos = sorted(g for g in por_grupo if g is not None and g not in ORDEN_GRUPOS)
    for grupo in grupos_no_canonicos:
        resultado.append((grupo, sorted(por_grupo[grupo])))
    if None in por_grupo:
        resultado.append((None, sorted(por_grupo[None])))
    return resultado


def _seccion_grupo_html(grupo: str | None, items: list[tuple[str, int]], catalogo: dict) -> str:
    color = GRUPO_COLOR.get(grupo, COLOR_POR_DEFECTO)
    color_texto = color_texto_legible(color)
    etiqueta = GRUPO_ETIQUETA.get(grupo, "Sin grupo / libre")
    filas = "".join(
        '<tr><td class="celda-check">☐</td>'
        f'<td class="celda-cantidad">{_esc(cantidad_real(alimento, equivalentes, catalogo))}</td>'
        f'<td class="celda-alimento">{_esc(alimento)}</td></tr>'
        for alimento, equivalentes in items
    )
    return (
        '<section class="grupo-bloque">'
        f'<h2 class="grupo-titulo" style="background:{color};color:{color_texto};">{_esc(etiqueta)}</h2>'
        f'<table class="tabla-lista">{filas}</table>'
        "</section>"
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
  font-size: 12pt;
  line-height: 1.35;
}}
header {{ margin-bottom: 4mm; }}
h1 {{ font-size: 18pt; margin: 0 0 1mm; }}
.subtitulo {{ font-size: 9pt; color: {_MUTED}; margin: 0; }}
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
.grupo-bloque {{ break-inside: avoid; page-break-inside: avoid; margin: 0 0 5mm; }}
.grupo-titulo {{
  margin: 0;
  padding: 1.5mm 3mm;
  font-size: 11.5pt;
  border-radius: 5px 5px 0 0;
}}
table.tabla-lista {{ width: 100%; border-collapse: collapse; }}
table.tabla-lista td {{
  border: 0.5pt solid {_BORDE};
  border-top: none;
  padding: 1.8mm 3mm;
  vertical-align: middle;
}}
table.tabla-lista tr:first-child td {{ border-top: 0.5pt solid {_BORDE}; }}
.celda-check {{ width: 8mm; text-align: center; font-size: 13pt; color: {_MUTED}; }}
.celda-cantidad {{ width: 32mm; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.nota {{ color: {_MUTED}; font-size: 9pt; font-style: italic; margin-top: 4mm; }}
@media print {{
  body {{ background: #fff; padding: 0; }}
  .solo-pantalla {{ display: none; }}
}}
@page {{ size: letter; margin: 10mm; }}
"""


def generar_html_lista_super(
    personas: list[str],
    equivalentes_por_alimento: dict[str, int],
    catalogo: dict[str, dict],
    notas: list[str],
) -> str:
    """`equivalentes_por_alimento`: ya consolidado entre TODAS las `personas` elegidas (mismo
    alimento de dos personas distintas suma en una sola línea -- eso lo resuelve
    `views/lista_super.py` antes de llamar aquí, con `sumar_por_grupo(ingredientes, "alimento",
    "equivalentes")` sobre los ingredientes de la semana de todas ellas). `notas`: texto libre ya
    armado por la vista (ej. referencias rotas en "Menú semanal") -- este módulo no vuelve a
    resolver Mongo, solo renderiza."""
    secciones = agrupar_alimentos_por_grupo(equivalentes_por_alimento, catalogo)
    cuerpo = (
        "".join(_seccion_grupo_html(g, items, catalogo) for g, items in secciones)
        if secciones
        else '<p class="nota">Sin ingredientes que comprar todavía.</p>'
    )
    notas_html = f'<p class="nota">{" ".join(_esc(n) for n in notas)}</p>' if notas else ""
    titulo_personas = " + ".join(personas)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Lista del súper — {_esc(titulo_personas)}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>🛒 Lista del súper — {_esc(titulo_personas)}</h1>
  <p class="subtitulo">Generado el {date.today().isoformat()} con EquiVale, sumando la semana
  asignada en "Menú semanal".</p>
  <p class="aviso-pantalla solo-pantalla">💡 Usa Ctrl/Cmd+P para imprimir esta página o guardarla como PDF.</p>
</header>
{cuerpo}
{notas_html}
</body>
</html>"""
