"""Paleta de color fija por grupo SMAE — identidad visual del grupo, no del estado
(exacto/falta/excedido). Ver UI-BUILD-YOUR-MENU.md -> "Convención de colores por grupo SMAE".
Single source of truth: no repetir estos hex en las páginas de Streamlit.
"""

GRUPO_COLOR = {
    "Fruta": "#FFC000",
    "Verdura": "#00A651",
    "Cereal": "#F07C22",
    "Leguminosa": "#FF0000",
    "AOA": "#A6081C",
    "Aceite s/p": "#3D4A1E",
    "Aceite c/p": "#6D6E71",
}

GRUPO_ETIQUETA = {
    "Fruta": "Fruta",
    "Verdura": "Verdura",
    "Cereal": "Cereal",
    "Leguminosa": "Leguminosas",
    "AOA": "AOA",
    "Aceite s/p": "Aceites s/proteína",
    "Aceite c/p": "Aceite c/proteína",
}

COLOR_POR_DEFECTO = "#555555"


def luminancia_relativa(color_hex: str) -> float:
    """Luminancia percibida (0-1) de un color hex, para elegir texto claro/oscuro legible."""
    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def color_texto_legible(color_hex: str) -> str:
    """Hex de texto (casi negro u casi blanco "Barro") legible sobre `color_hex` de fondo -- mismo
    criterio en todos los usos de GRUPO_COLOR, para no listar excepciones a mano (ej. Fruta es
    claro y necesita texto oscuro). Compartido entre `chip_html` (HTML de la app) y
    `nutriguia/html_semanal.py` (HTML imprimible del "Menú semanal") para que un mismo grupo se
    vea igual de legible en ambos."""
    return "#2B2621" if luminancia_relativa(color_hex) > 0.6 else "#F7F4EE"


def chip_html(grupo: str, texto: str) -> str:
    """Badge HTML con el color del grupo, para usar con st.markdown(unsafe_allow_html=True).
    Estilo "Barro" (ver UI-BUILD-YOUR-MENU.md -> Convención de colores): pastilla tipo ficha de
    conteo SMAE, con texto oscuro automático sobre colores claros (ej. Fruta) para mantener
    contraste legible sin tener que listar excepciones a mano.
    """
    color = GRUPO_COLOR.get(grupo, COLOR_POR_DEFECTO)
    color_texto = color_texto_legible(color)
    es_claro = color_texto == "#2B2621"
    color_punto = "rgba(43,38,33,.35)" if es_claro else "rgba(255,255,255,.65)"
    return (
        f'<span style="background-color:{color}; color:{color_texto}; font-weight:600; '
        f"padding:.32rem .7rem; border-radius:999px; display:inline-flex; align-items:center; "
        f"gap:.4rem; font-size:.86rem; font-family:'Figtree',ui-sans-serif,sans-serif; "
        f"box-shadow:0 1px 0 rgba(255,255,255,.25) inset, 0 1px 1px rgba(43,38,33,.05), "
        f'0 3px 8px -3px rgba(43,38,33,.18);">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{color_punto};'
        f'display:inline-block;flex-shrink:0;"></span>{texto}</span>'
    )


def chip_muted_html(texto: str) -> str:
    """Badge HTML neutro y de menor saturación que `chip_html` -- para info secundaria que NO es
    un grupo SMAE (ej. en qué tiempo típico se ve normalmente una receta que no es la que se está
    armando ahora mismo; ver "Menú del día" -> selector de recetas)."""
    return (
        '<span style="background-color:rgba(43,38,33,.06); color:rgba(43,38,33,.62); '
        "font-weight:500; padding:.3rem .7rem; border-radius:999px; display:inline-flex; "
        "align-items:center; font-size:.82rem; font-family:'Figtree',ui-sans-serif,sans-serif; "
        'border:1px solid rgba(43,38,33,.14); white-space:nowrap;">'
        f"{texto}</span>"
    )
