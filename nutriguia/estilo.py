"""Identidad visual "Barro" -- CSS compartido por toda la app (UI, no aritmética).

Se inyecta UNA sola vez desde app.py, antes de pagina.run(), y aplica a todas las páginas de
views/ porque app.py se re-ejecuta completo en cada navegación de st.navigation.

Los colores base (fondo, superficie, texto, acento) viven en .streamlit/config.toml -- Streamlit
los aplica de forma nativa (botones "primary", inputs, sidebar). Este módulo solo agrega lo que
config.toml no cubre: tipografía (Google Fonts), radios/sombras "de barro", y el estilo puntual de
elementos concretos vía la clase `st-key-<key>` que Streamlit agrega a cualquier widget/contenedor
con un `key=` explícito (mecanismo oficial para CSS dirigido, ver docs de Streamlit -- más estable
que apuntar a las clases `st-emotion-cache-*`, que son hashes que cambian entre builds).

Convención de `key=` para que este CSS los alcance (ver views/build_your_menu.py):
- botones "-" de un stepper: key que empieza con "menos_"
- botones "+" de un stepper: key que empieza con "mas_"
- contenedor de una receta agregada: key que empieza con "receta_card_"
- contenedor del panel de estado (por tiempo o del día): key que empieza con "status_"
"""

import streamlit as st

GOOGLE_FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Fraunces:ital,wght@0,500;0,600;1,500"
    "&family=Figtree:wght@400;500;600;700"
    "&family=Space+Mono:wght@400;700"
    '&display=swap" rel="stylesheet">'
)

CSS = """
<style>
:root{
  --barro-radius-card: 22px;
  --barro-radius-btn: 14px;
  --barro-radius-pill: 999px;
  --barro-border: rgba(43,38,33,.14);
  --barro-shadow: 0 1px 1px rgba(43,38,33,.05), 0 6px 16px -8px rgba(43,38,33,.22);
}

/* --- Tipografía --- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea {
  font-family: "Figtree", ui-sans-serif, system-ui, sans-serif;
}
.stApp h1, .stApp h2, .stApp h3 {
  font-family: "Fraunces", ui-serif, Georgia, serif;
  font-weight: 560;
  letter-spacing: -.01em;
}
.stApp [data-testid="stDateInput"] input,
.stApp code {
  font-family: "Space Mono", ui-monospace, monospace !important;
}

/* --- Botones: base tipo pastilla táctil --- */
.stButton button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
  border-radius: var(--barro-radius-pill) !important;
  box-shadow: var(--barro-shadow);
  transition: transform .08s ease;
}
.stButton button:active { transform: scale(.97); }

/* Steppers +/- de "Build your menu": cuadrados pequeños, no pastillas alargadas
   (ver convención de `key=` arriba: menos_* / mas_*) */
div[class*="st-key-menos_"] .stButton button,
div[class*="st-key-mas_"] .stButton button {
  border-radius: var(--barro-radius-btn) !important;
  min-width: 2.4rem;
  width: 2.4rem;
  padding: 0;
  font-weight: 700;
}

/* --- Tarjetas: recetas agregadas y panel de estado --- */
div[class*="st-key-receta_card_"] [data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-status_"] [data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--barro-radius-card) !important;
  border-color: var(--barro-border) !important;
  box-shadow: var(--barro-shadow);
}

/* --- Tabs de tiempos del día: pastillas horizontales con scroll táctil --- */
.stTabs [role="tablist"] {
  gap: .35rem;
  overflow-x: auto;
}
.stTabs [data-testid="stTab"] {
  border-radius: var(--barro-radius-pill);
  border: 1px solid var(--barro-border);
}

/* --- Selects, fechas, checkboxes, expander: radios suaves consistentes --- */
.stSelectbox [data-rac] > div,
.stDateInput input,
.stTextInput input,
.stNumberInput input,
.stExpander {
  border-radius: var(--barro-radius-btn) !important;
}

/* --- Navegación lateral --- */
a[data-testid="stSidebarNavLink"] {
  border-radius: var(--barro-radius-btn);
  margin: .1rem .3rem;
}
a[data-testid="stSidebarNavLink"][aria-current="page"] {
  box-shadow: var(--barro-shadow);
}

/* --- Respeta preferencia de movimiento reducido --- */
@media (prefers-reduced-motion: reduce) {
  .stButton button { transition: none; }
}
</style>
"""


def inyectar_css() -> None:
    """Inyecta fuentes + <style> en la página actual. Dos st.markdown() separados a propósito:
    concatenar todo en una sola llamada rompía el CSS -- el parser de Markdown de Streamlit
    detecta un bloque HTML "tipo 6" (lista fija de tags, incluye <link>) que termina en la
    primera línea en blanco, así que cualquier línea en blanco DENTRO del <style> (que sí van
    todas juntas si <style> queda pegado a los <link> sin blanco de por medio) cortaba el bloque
    a la mitad y el resto del CSS se mostraba como texto plano en la página. Al separar, el
    <style> empieza su propia línea desde el carácter 0 y Streamlit lo reconoce como bloque HTML
    "tipo 1" (script/pre/style/textarea), que sí tolera líneas en blanco adentro.
    """
    st.markdown(GOOGLE_FONTS_LINK, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)
