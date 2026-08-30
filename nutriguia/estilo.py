"""Identidad visual "Barro" -- CSS compartido por toda la app (UI, no aritmética).

Se inyecta UNA sola vez desde app.py, antes de pagina.run(), y aplica a todas las páginas de
views/ porque app.py se re-ejecuta completo en cada navegación de st.navigation.

Los colores base (fondo, superficie, texto, acento) viven en .streamlit/config.toml -- Streamlit
los aplica de forma nativa (botones "primary", inputs, sidebar). Este módulo solo agrega lo que
config.toml no cubre: tipografía (Google Fonts), radios/sombras "de barro", y el estilo puntual de
elementos concretos vía la clase `st-key-<key>` que Streamlit agrega a cualquier widget/contenedor
con un `key=` explícito (mecanismo oficial para CSS dirigido, ver docs de Streamlit -- más estable
que apuntar a las clases `st-emotion-cache-*`, que son hashes que cambian entre builds).

Convención de `key=` para que este CSS los alcance (ver views/menu_del_dia.py):
- botones "-" de un stepper: key que empieza con "menos_"
- botones "+" de un stepper: key que empieza con "mas_"
- contenedor de una receta agregada: key que empieza con "receta_card_"
- contenedor del panel de estado (por tiempo o del día): key que empieza con "status_"
- expander colapsable de ingredientes de una receta agregada (2026-08-29): key que empieza con
  "exp_receta_" -- comparte la regla general `.stExpander` de abajo (radio "de barro") y además
  tiene su propia regla (2026-08-30, a pedido del usuario) que agranda/engrosa el texto del título
  (el nombre del platillo) para distinguirlo de un vistazo de los ingredientes de adentro (texto
  normal). El `key=` incluye un número de "epoch" (`f"exp_receta_{id}_{epoch}"`) que sube cada vez
  que se agrega otra receta al mismo tiempo -- `st.expander` no respeta `expanded=` en reruns donde
  su key ya existía (a diferencia de widgets "de valor" como `st.checkbox`), así que forzar el
  colapso de una receta ya agregada requiere una key nueva, no solo cambiar `session_state` (ver
  `_renderizar_tiempo()` en `views/menu_del_dia.py`).

**Vista oscura (2026-08-30, a pedido del usuario, para leer de noche)**: `.streamlit/config.toml`
ahora define `[theme.light]`/`[theme.dark]` -- Streamlit 1.62 los soporta de forma nativa
(confirmado en el código fuente instalado, `CustomThemeCategories.LIGHT`/`DARK`) y agrega solo un
selector System/Light/Dark en el menú ⋮ que reteñe TODOS sus componentes nativos sin código
adicional. Este módulo solo cubre lo que Streamlit no puede reteñir por sí solo -- el HTML/CSS
propio (el diagrama de "Guía") y los acentos de borde/sombra de más abajo -- con variables CSS
(`--surface`, `--ink`, `--accent`, etc.) que cambian bajo `@media (prefers-color-scheme: dark)`.
Ver el bloque `:root`/`@media` de abajo para el detalle y la limitación conocida (KC-004).
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

  /* Tokens "Barro" para HTML propio inyectado con unsafe_allow_html (ej. el diagrama de "Guía",
     views/guia.py) -- Streamlit NO expone los colores del tema activo como variables CSS
     reutilizables (los aplica por componente vía JS/emotion, confirmado inspeccionando la app en
     vivo), así que cualquier HTML/CSS propio necesita su propia fuente de verdad de color en vez
     de adivinar. views/guia.py ya escribía `var(--surface, #F7F4EE)` etc. con esa intención desde
     que se creó, pero estas variables nunca se definían -- siempre caían al valor de respaldo
     (claro), por eso el diagrama se veía como un rectángulo claro fijo sobre fondo oscuro en modo
     oscuro (2026-08-30, ver BUGS.md). */
  --surface: #F7F4EE;
  --surface-2: #FBF9F5;
  --border: #DAD3C4;
  --ink: #2B2621;
  --ink-faint: #97897A;
  --accent: #3C6E68;
}

/* Vista oscura (2026-08-30, a pedido del usuario, para leer de noche) -- sigue la preferencia del
   SISTEMA/navegador (`prefers-color-scheme`), lo mismo que activa "System" en el selector nativo
   de Streamlit (menú ⋮ -> System/Light/Dark, ver .streamlit/config.toml [theme.light]/[theme.
   dark]). Streamlit mismo ya reteñe sus propios componentes nativos sin necesitar nada de esto --
   estas variables solo cubren el HTML/CSS propio de la app (el diagrama de "Guía" y los acentos
   de borde/sombra de abajo), que de otro modo se quedarían con la paleta clara fija.
   Limitación conocida (KC-004, BUGS.md): si alguien elige "Dark" a mano en ese menú mientras su
   sistema operativo sigue en claro, `prefers-color-scheme` no se entera (es una preferencia del
   SO, no de la app) -- Streamlit sí se pone oscuro pero el diagrama de Guía y estos acentos se
   quedan en su versión clara hasta que el sistema operativo también cambie. Caso raro en la
   práctica (la mayoría deja "System" y su SO cambia solo de noche), documentado en vez de resuelto
   porque Streamlit no expone su tema activo real a CSS/JS de ninguna otra forma. */
@media (prefers-color-scheme: dark) {
  :root {
    --barro-border: rgba(241,236,227,.16);
    --barro-shadow: 0 1px 1px rgba(0,0,0,.3), 0 6px 16px -8px rgba(0,0,0,.6);

    --surface: #2E2822;
    --surface-2: #221D19;
    --border: #4A4136;
    --ink: #F1ECE3;
    --ink-faint: #B7A999;
    --accent: #6FB0A5;
  }
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

/* Steppers +/- de "Menú del día": cuadrados pequeños, no pastillas alargadas
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

/* Nombre del platillo (título del expander colapsable de "Menú del día") un poco más grande y
   con más peso que los ingredientes de adentro (texto normal) -- a pedido del usuario,
   2026-08-30, para distinguir de un vistazo el nombre de la receta de su lista de ingredientes.
   Selector por `data-testid`, no por la clase con hash de Streamlit (cambia entre builds) -- ver
   convención de `key=` arriba: `exp_receta_`. */
div[class*="st-key-exp_receta_"] summary [data-testid="stMarkdownContainer"] p {
  font-size: 1.08rem;
  font-weight: 700;
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
