"""EquiVale — punto de entrada. Navegación lateral entre "Build your menu" y el editor de recetas.

Ver UI-BUILD-YOUR-MENU.md para la especificación de cada página.
"""

import streamlit as st

st.set_page_config(page_title="EquiVale", page_icon="🥗", layout="wide")

pagina = st.navigation(
    [
        st.Page("pages/build_your_menu.py", title="Build your menu", icon="🥗"),
        st.Page("pages/editor_recetas.py", title="Editor de recetas", icon="🧑‍🍳"),
    ]
)
pagina.run()
