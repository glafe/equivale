"""EquiVale — punto de entrada. Navegación lateral entre las páginas de la app.

Ver UI-BUILD-YOUR-MENU.md para la especificación de cada página.
"""

import streamlit as st

from nutriguia.estilo import inyectar_css

st.set_page_config(page_title="EquiVale", page_icon="🥗", layout="wide")
inyectar_css()

pagina = st.navigation(
    {
        # Agrupado por lo que un usuario común busca, no por cómo está hecho por dentro (ver
        # UI-BUILD-YOUR-MENU.md -> "Navegación" para el razonamiento). "Menú del día" sigue
        # siendo la página de entrada (default=True) aunque "Guía" salga primero en la lista --
        # el usuario ya sabe usar la app día a día, no queremos forzarle la guía cada vez.
        "Guía": [
            st.Page("views/guia.py", title="Cómo funciona", icon="📖"),
        ],
        "Tu día a día": [
            st.Page("views/menu_del_dia.py", title="Menú del día", icon="🥗", default=True),
            st.Page("views/menu_semanal.py", title="Menú semanal", icon="🗓️"),
            st.Page("views/lista_super.py", title="Lista del súper", icon="🛒"),
        ],
        "Tus recetas": [
            st.Page("views/editor_recetas.py", title="Recetas", icon="🧑‍🍳"),
            st.Page("views/editor_ingredientes.py", title="Ingredientes", icon="🥕"),
        ],
        "Cuenta": [
            st.Page("views/personas.py", title="Personas", icon="🧑‍🤝‍🧑"),
        ],
        "Ajustes": [
            st.Page("views/configuracion.py", title="Configuración", icon="⚙️"),
        ],
    }
)
pagina.run()
