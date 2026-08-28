"""EquiVale — punto de entrada. Navegación lateral entre las páginas de la app.

Ver UI-BUILD-YOUR-MENU.md para la especificación de cada página.
"""

import streamlit as st

from nutriguia.estilo import inyectar_css

st.set_page_config(page_title="EquiVale", page_icon="🥗", layout="wide")
inyectar_css()

pagina = st.navigation(
    [
        st.Page("views/build_your_menu.py", title="Build your menu", icon="🥗"),
        st.Page("views/editor_recetas.py", title="Editor de recetas", icon="🧑‍🍳"),
        st.Page("views/editor_ingredientes.py", title="Editor de ingredientes", icon="🥕"),
        st.Page("views/personas.py", title="Personas", icon="🧑‍🤝‍🧑"),
    ]
)
pagina.run()
