"""EquiVale — "Guía": página de ayuda muy simple para usuarios que no conocen la app (2026-08-29,
a pedido del usuario). Lo primero que se ve es un diagrama de cómo se relacionan los objetos del
sistema (Ingredientes -> Recetas -> Menú semanal / Menú del día, con Personas como quién y su
objetivo) -- interactivo con enlaces reales (`<a href>`, navegación normal del navegador, no hace
falta `st.switch_page`) y resaltado por CSS puro (`:has()`) al pasar el cursor.

CSS y HTML van en llamadas a st.markdown SEPARADAS a propósito (una para el <style>, otra para el
<div> del diagrama) -- ver BUGS.md BUG-005: concatenar <style> con otro contenido en una sola
llamada rompió el CSS de la identidad Barro (el parser de Markdown de Streamlit corta el bloque en
la primera línea en blanco si el <style> no empieza su propia línea desde el carácter 0).

Ver UI-BUILD-YOUR-MENU.md -> "Guía" para la especificación completa.
"""

import streamlit as st

DIAGRAMA_CSS = """
<style>
.eqv-guia-wrap{ overflow-x:auto; padding-bottom:.4rem; margin:1.3rem 0 .5rem; }
.eqv-guia-diagrama{
  display:grid;
  min-width:640px;
  grid-template-columns: repeat(5, auto);
  grid-template-rows: repeat(5, auto);
  grid-template-areas:
    ".   .    personas .   ."
    ".   .    a-pv     .   ."
    "ing a-1  recetas  a-2 semanal"
    ".   .    a-rd     .   ."
    ".   .    diario   .   .";
  gap:.35rem 1.1rem;
  align-items:center;
  justify-items:center;
  padding:1.3rem 1.1rem;
  background:var(--surface-2, #FBF9F5);
  border:1px solid var(--border, #DAD3C4);
  border-radius:22px;
}
.eqv-node{
  display:flex; flex-direction:column; align-items:center; gap:.15rem;
  text-decoration:none;
  color:var(--ink, #2B2621);
  background:var(--surface, #F7F4EE);
  border:1.5px solid var(--border, #DAD3C4);
  border-radius:16px;
  padding:.75rem 1rem;
  min-width:118px;
  text-align:center;
  font-family:"Figtree", ui-sans-serif, sans-serif;
  font-weight:600;
  font-size:.85rem;
  transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease, background .12s ease;
}
.eqv-node .ico{ font-size:1.5rem; line-height:1; }
.eqv-node .sub{ font-size:.72rem; font-weight:400; color:var(--ink-faint, #97897A); }
.eqv-node:hover{
  transform:translateY(-3px);
  border-color:var(--accent, #3C6E68);
  box-shadow:0 8px 18px -10px rgba(43,38,33,.35);
}
#n-ing{ grid-area:ing; }
#n-recetas{ grid-area:recetas; }
#n-semanal{ grid-area:semanal; }
#n-diario{ grid-area:diario; }
#n-personas{ grid-area:personas; }

.eqv-arrow{ grid-area:a-1; font-size:0; color:var(--ink-faint, #97897A); font-weight:700; }
.eqv-arrow::after{ font-size:1.35rem; }
#a-1::after{ content:"→"; }
#a-2{ grid-area:a-2; }
#a-2::after{ content:"→"; }
#a-pv{ grid-area:a-pv; }
#a-pv::after{ content:"↓"; }
#a-rd{ grid-area:a-rd; }
#a-rd::after{ content:"↓"; }

/* Resaltado por CSS puro (:has -- navegadores modernos; en uno viejo simplemente no resalta,
   los enlaces y el hover individual de cada nodo siguen funcionando igual). */
.eqv-guia-diagrama:has(#n-ing:hover) #n-recetas,
.eqv-guia-diagrama:has(#n-ing:hover) #a-1{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-recetas:hover) #n-ing,
.eqv-guia-diagrama:has(#n-recetas:hover) #n-semanal,
.eqv-guia-diagrama:has(#n-recetas:hover) #n-diario,
.eqv-guia-diagrama:has(#n-recetas:hover) #a-1,
.eqv-guia-diagrama:has(#n-recetas:hover) #a-2,
.eqv-guia-diagrama:has(#n-recetas:hover) #a-rd{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-semanal:hover) #n-recetas,
.eqv-guia-diagrama:has(#n-semanal:hover) #n-personas,
.eqv-guia-diagrama:has(#n-semanal:hover) #a-2,
.eqv-guia-diagrama:has(#n-semanal:hover) #a-pv{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-diario:hover) #n-recetas,
.eqv-guia-diagrama:has(#n-diario:hover) #a-rd{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-personas:hover) #n-semanal,
.eqv-guia-diagrama:has(#n-personas:hover) #a-pv{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }
</style>
"""

DIAGRAMA_HTML = """
<div class="eqv-guia-wrap">
  <div class="eqv-guia-diagrama">
    <a id="n-personas" class="eqv-node" href="/personas">
      <span class="ico">🧑‍🤝‍🧑</span>Personas<span class="sub">quién, y su objetivo diario</span>
    </a>
    <div id="a-pv" class="eqv-arrow"></div>
    <a id="n-ing" class="eqv-node" href="/editor_ingredientes">
      <span class="ico">🥕</span>Ingredientes<span class="sub">el catálogo base</span>
    </a>
    <div id="a-1" class="eqv-arrow"></div>
    <a id="n-recetas" class="eqv-node" href="/editor_recetas">
      <span class="ico">🧑‍🍳</span>Recetas<span class="sub">platillos armados con ingredientes</span>
    </a>
    <div id="a-2" class="eqv-arrow"></div>
    <a id="n-semanal" class="eqv-node" href="/menu_semanal">
      <span class="ico">🗓️</span>Menú semanal<span class="sub">ciclo de menús por día</span>
    </a>
    <div id="a-rd" class="eqv-arrow"></div>
    <a id="n-diario" class="eqv-node" href="/menu_del_dia">
      <span class="ico">🥗</span>Menú del día<span class="sub">un día suelto, por fecha</span>
    </a>
  </div>
</div>
"""


def render() -> None:
    st.title("📖 Cómo funciona EquiVale")
    st.caption(
        "Una guía muy corta -- si ya le agarraste el modo, no necesitas leer esto cada vez."
    )

    st.markdown(
        "EquiVale arma tus comidas contando **equivalentes SMAE** (porciones estándar por grupo "
        "de alimento) en vez de calorías. Todo se construye a partir de las mismas piezas, en "
        "este orden:"
    )

    st.markdown(DIAGRAMA_CSS, unsafe_allow_html=True)
    st.markdown(DIAGRAMA_HTML, unsafe_allow_html=True)
    st.caption(
        "Pasa el cursor sobre un cuadro para ver con qué se conecta. Haz clic para ir directo a "
        "esa página."
    )

    st.divider()
    st.subheader("Para armar tu primer Menú semanal")
    st.markdown(
        """
1. Ve a **Personas** y crea a la persona, con su objetivo diario (cuánto debe comer de cada
   grupo al día).
2. Revisa **Ingredientes** — si falta alguno, agrégalo a mano o con "Agregar de SMAE".
3. Arma o revisa tus **Recetas** — cada una ya suma sus equivalentes por grupo sola, no hay que
   calcular nada a mano.
4. Ve a **Menú semanal**: crea uno o más menús eligiendo recetas por tiempo del día, y asigna
   cada uno a los días de la semana que le toque (deja "Libre" los días de descanso).
5. Para un día suelto que no sigue tu ciclo normal (un antojo, una comida especial), usa
   **Menú del día** en vez de esperar a que le toque en el ciclo semanal.
6. Si algo se ve raro más adelante (un ingrediente sin catalogar, nombres repetidos), **Configuración**
   te ayuda a encontrarlo y corregirlo.
        """
    )
    st.caption(
        "\"Menú semanal\" y \"Menú del día\" son cosas distintas: el semanal es tu ciclo "
        "de siempre (se repite); el del día es lo que de verdad guardaste para una fecha exacta."
    )


render()
