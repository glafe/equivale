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


def chip_html(grupo: str, texto: str) -> str:
    """Badge HTML con el color del grupo, para usar con st.markdown(unsafe_allow_html=True)."""
    color = GRUPO_COLOR.get(grupo, COLOR_POR_DEFECTO)
    return (
        f'<span style="background-color:{color}; color:white; font-weight:bold; '
        f'font-style:italic; padding:2px 10px; border-radius:6px; display:inline-block;">'
        f"{texto}</span>"
    )
