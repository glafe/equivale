"""EquiVale — "Guía": página de ayuda muy simple para usuarios que no conocen la app (2026-08-29,
a pedido del usuario). Lo primero que se ve es un diagrama de cómo se relacionan los objetos del
sistema -- interactivo, con enlaces a cada página y resaltado por CSS puro (`:has()`) al pasar el
cursor.

**Corregido el mismo día** tras aclaración del usuario: el flujo real es lineal, no una rama --
"Menú semanal" NO arma recetas por su cuenta, solo asigna días de "Menú del día" ya guardados con
nombre a los días de la semana (ver docstring de `views/menu_semanal.py`). La primera versión de
este diagrama tenía a "Menú semanal" y "Menú del día" como dos ramas separadas saliendo de
"Recetas" -- ya no es así, ahora "Menú del día" es un paso intermedio obligado:
`Ingredientes -> Recetas -> Menú del día -> Menú semanal`, con Personas alimentando a "Menú del
día" (ahí es donde se compara contra el objetivo, y donde se le pone nombre a un día para poder
reusarlo).

CSS y HTML van en llamadas a st.markdown SEPARADAS a propósito (una para el <style>, otra para el
<div> del diagrama) -- ver BUGS.md BUG-005: concatenar <style> con otro contenido en una sola
llamada rompió el CSS de la identidad Barro (el parser de Markdown de Streamlit corta el bloque en
la primera línea en blanco si el <style> no empieza su propia línea desde el carácter 0).

Los nodos son `<a href="...">` -- Streamlit fuerza `target="_blank" rel="noopener noreferrer"`
en TODO `<a>` que renderiza vía markdown (incluso con `unsafe_allow_html=True`, e incluso para un
href relativo/interno como estos) y además elimina cualquier atributo `onclick` que se le ponga
(medida de sanitización, no algo configurable) -- así que un clic aquí abre la página destino en
una pestaña nueva, nunca navega en el mismo lugar. Confirmado en `BUGS.md` BUG-008: no es un bug
de esta página, es cómo Streamlit sanitiza `<a>` en markdown -- no intentar forzar navegación en
el mismo lugar con JS, se elimina de todas formas.

Ver UI-BUILD-YOUR-MENU.md -> "Guía" para la especificación completa.
"""

import streamlit as st

DIAGRAMA_CSS = """
<style>
.eqv-guia-wrap{ overflow-x:auto; padding-bottom:.4rem; margin:1.3rem 0 .5rem; }
.eqv-guia-diagrama{
  display:grid;
  min-width:760px;
  grid-template-columns: repeat(7, auto);
  grid-template-rows: repeat(3, auto);
  grid-template-areas:
    ".   .    .        .   personas .   ."
    ".   .    .        .   a-pv     .   ."
    "ing a-1  recetas  a-2 diario   a-3 semanal";
  gap:.35rem 1.1rem;
  align-items:center;
  justify-items:center;
  padding:1.3rem 1.1rem;
  background:var(--surface-2, #FBF9F5);
  border:1px solid var(--border, #DAD3C4);
  border-radius:22px;
}
/* Streamlit aplica su propio color/subrayado a <a> dentro de contenido markdown con un selector
   más específico que una sola clase -- .eqv-node solo no alcanza a ganarle. De ahí el
   `a.eqv-node` (más específico) + !important en color/subrayado, mismo recurso que ya usa
   nutriguia/estilo.py para pelear contra estilos nativos de Streamlit. */
a.eqv-node, a.eqv-node:visited{
  display:flex; flex-direction:column; align-items:center; gap:.15rem;
  text-decoration:none !important;
  color:var(--ink, #2B2621) !important;
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
.eqv-node .sub{ font-size:.72rem; font-weight:400; color:var(--ink-faint, #97897A) !important; text-decoration:none !important; }
.eqv-node:hover{
  transform:translateY(-3px);
  border-color:var(--accent, #3C6E68);
  box-shadow:0 8px 18px -10px rgba(43,38,33,.35);
}
#n-ing{ grid-area:ing; }
#n-recetas{ grid-area:recetas; }
#n-diario{ grid-area:diario; }
#n-semanal{ grid-area:semanal; }
#n-personas{ grid-area:personas; }

.eqv-arrow{ font-size:0; color:var(--ink-faint, #97897A); font-weight:700; }
.eqv-arrow::after{ font-size:1.35rem; }
#a-1{ grid-area:a-1; } #a-1::after{ content:"→"; }
#a-2{ grid-area:a-2; } #a-2::after{ content:"→"; }
#a-3{ grid-area:a-3; } #a-3::after{ content:"→"; }
#a-pv{ grid-area:a-pv; } #a-pv::after{ content:"↓"; }

/* Resaltado por CSS puro (:has -- navegadores modernos; en uno viejo simplemente no resalta,
   los enlaces y el hover individual de cada nodo siguen funcionando igual). Cadena lineal:
   Ingredientes -> Recetas -> Menú del día -> Menú semanal, con Personas alimentando a Menú del
   día (ahí se compara contra el objetivo y se le pone nombre a un día para reutilizarlo). */
.eqv-guia-diagrama:has(#n-ing:hover) #n-recetas,
.eqv-guia-diagrama:has(#n-ing:hover) #a-1{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-recetas:hover) #n-ing,
.eqv-guia-diagrama:has(#n-recetas:hover) #n-diario,
.eqv-guia-diagrama:has(#n-recetas:hover) #a-1,
.eqv-guia-diagrama:has(#n-recetas:hover) #a-2{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-diario:hover) #n-recetas,
.eqv-guia-diagrama:has(#n-diario:hover) #n-semanal,
.eqv-guia-diagrama:has(#n-diario:hover) #n-personas,
.eqv-guia-diagrama:has(#n-diario:hover) #a-2,
.eqv-guia-diagrama:has(#n-diario:hover) #a-3,
.eqv-guia-diagrama:has(#n-diario:hover) #a-pv{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-semanal:hover) #n-diario,
.eqv-guia-diagrama:has(#n-semanal:hover) #a-3{ border-color:var(--accent, #3C6E68); color:var(--accent, #3C6E68); }

.eqv-guia-diagrama:has(#n-personas:hover) #n-diario,
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
    <a id="n-diario" class="eqv-node" href="/menu_del_dia">
      <span class="ico">🥗</span>Menú del día<span class="sub">un día armado, con o sin nombre</span>
    </a>
    <div id="a-3" class="eqv-arrow"></div>
    <a id="n-semanal" class="eqv-node" href="/menu_semanal">
      <span class="ico">🗓️</span>Menú semanal<span class="sub">asigna días con nombre a la semana</span>
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
        "Pasa el cursor sobre un cuadro para ver con qué se conecta. Haz clic para abrir esa "
        "página en una pestaña nueva."
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
4. Arma un día en **Menú del día** como cualquier otro, y guárdalo con un **nombre** (ej.
   "Menú 1") además de su fecha — eso es lo que lo vuelve reutilizable.
5. Ve a **Menú semanal** y asigna ese nombre a los días de la semana que le toquen (deja "Libre"
   los días de descanso). Repite el paso 4 para cada menú distinto que quieras tener en tu ciclo
   (ej. "Menú 2").
6. Para un día suelto que no sigue tu ciclo normal (un antojo, una comida especial), usa
   **Menú del día** sin ponerle nombre.
7. Si algo se ve raro más adelante (un ingrediente sin catalogar, nombres repetidos),
   **Configuración** te ayuda a encontrarlo y corregirlo.
        """
    )
    st.caption(
        "\"Menú semanal\" no arma recetas por su cuenta -- solo organiza días de \"Menú del "
        "día\" que ya guardaste con nombre. Todo el detalle (qué recetas, cuántos equivalentes, "
        "ajustar porciones) se sigue armando ahí."
    )


render()
