"""EquiVale — "Configuración": panel de administración que no encaja en las páginas de uso
diario. Por ahora trae "Integridad de datos" -- Mongo no valida las relaciones entre colecciones
(son referencias por nombre/id sueltas, no llaves foráneas: un `ingrediente.alimento` que apunta
a `catalogo_alimentos`, un `receta_id` que apunta a `recetas`, etc.), así que nada avisa cuando
una de esas referencias se rompe (se elimina el alimento/receta del lado "dueño" pero no se
actualiza quien lo usaba). Esta página junta herramientas de búsqueda ("¿dónde se usa X?") y
chequeos automáticos ("¿qué referencias ya están rotas?"), cada uno independiente.

Ver UI-BUILD-YOUR-MENU.md -> "Configuración" para la especificación completa.
"""

import difflib

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import (
    cargar_catalogo,
    cargar_objetivo,
    cargar_personas,
    cargar_recetas,
    db,
    invalidar_cache_catalogo,
    invalidar_cache_recetas,
)
from nutriguia.texto import normalizar_busqueda
from nutriguia.validation import sumar_por_grupo

TIEMPO_LABEL = {
    "al_despertar": "Al despertar", "desayuno": "Desayuno", "colacion": "Colación",
    "comida": "Comida", "cena": "Cena",
}
SIN_SELECCION = "— Elige uno —"


def _selectbox_seguro(label: str, opciones: list[str], key: str, **kwargs):
    """Mismo patrón que en las demás páginas: si el valor guardado para `key` ya no está en
    `opciones` (ej. se catalogó/eliminó algo mientras el selector seguía apuntando al valor
    viejo), lo limpia antes de instanciar el widget en vez de dejar que Streamlit truene."""
    if key in st.session_state and st.session_state[key] not in opciones:
        del st.session_state[key]
    return st.selectbox(label, options=opciones, key=key, **kwargs)


def _chips(vector: dict) -> str:
    if not vector:
        return "_(sin equivalentes)_"
    return " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(vector.items()))


# ---------------------------------------------------------------------------
# Sección A: buscar relaciones (lookup manual)
# ---------------------------------------------------------------------------

def _buscar_recetas_de_ingrediente():
    st.subheader("¿En qué recetas se usa un ingrediente?")
    catalogo = cargar_catalogo()
    recetas = cargar_recetas()
    nombres = [SIN_SELECCION] + sorted(catalogo.keys())
    elegido = _selectbox_seguro("Ingrediente", nombres, key="config_buscar_ingrediente")
    if elegido == SIN_SELECCION:
        return
    usos = [r for r in recetas if any(ing["alimento"] == elegido for ing in r["ingredientes"])]
    if not usos:
        st.caption(f"'{elegido}' no se usa en ninguna receta todavía.")
        return
    st.caption(f"Usado en {len(usos)} receta(s):")
    for r in usos:
        ing = next(i for i in r["ingredientes"] if i["alimento"] == elegido)
        etiquetas = []
        if ing.get("bloqueado"):
            etiquetas.append("bloqueado")
        if ing.get("opcional"):
            etiquetas.append("opcional")
        sufijo = f" _({', '.join(etiquetas)})_" if etiquetas else ""
        st.markdown(f"- **{r['nombre']}** — {ing['equivalentes']} equivalente(s){sufijo}")


def _buscar_uso_de_receta():
    st.subheader("¿Dónde se usa una receta?")
    recetas = cargar_recetas()
    recetas_por_id = {r["receta_id"]: r for r in recetas}
    nombres = [SIN_SELECCION] + sorted(recetas_por_id, key=lambda rid: recetas_por_id[rid]["nombre"])
    elegido = _selectbox_seguro(
        "Receta", nombres, key="config_buscar_receta",
        format_func=lambda rid: rid if rid == SIN_SELECCION else recetas_por_id[rid]["nombre"],
    )
    if elegido == SIN_SELECCION:
        return

    dias = list(db().menus_construidos.find({}, {"_id": 0}))
    en_dias = [
        (doc["persona"], doc["fecha"], tiempo)
        for doc in dias
        for tiempo, datos in doc.get("tiempos", {}).items()
        if any(inst["receta_id"] == elegido for inst in datos.get("seleccion", []))
    ]
    plantillas = list(db().plantillas_semana.find({}, {"_id": 0}))
    en_plantillas = [
        (p["persona"], p["nombre"], tiempo)
        for p in plantillas
        for tiempo, lista in p["tiempos"].items()
        if any(r["receta_id"] == elegido for r in lista)
    ]

    if not en_dias and not en_plantillas:
        st.caption("No aparece en ningún día guardado ni menú semanal todavía.")
        return
    if en_plantillas:
        st.caption(f"En {len(en_plantillas)} menú(s) semanal(es):")
        for persona, nombre, tiempo in en_plantillas:
            st.markdown(f"- **{nombre}** ({persona}) — {TIEMPO_LABEL.get(tiempo, tiempo)}")
    if en_dias:
        st.caption(f"En {len(en_dias)} día(s) guardado(s) de 'Menú del día':")
        for persona, fecha, tiempo in en_dias:
            st.markdown(f"- {persona} — {fecha} — {TIEMPO_LABEL.get(tiempo, tiempo)}")


# ---------------------------------------------------------------------------
# Sección B: chequeos automáticos (solo muestran problemas, no listas completas)
# ---------------------------------------------------------------------------

def _check_ingredientes_huerfanos():
    with st.expander("🥕 Ingredientes de recetas que ya no están en el catálogo", expanded=True):
        st.caption(
            "Una receta guarda cada ingrediente por nombre -- si ese alimento se elimina del "
            "catálogo (o nunca se catalogó), el ingrediente se vuelve \"no ajustable\" en vez de "
            "romperse, pero puede pasar desapercibido. Catalogarlo aquí arregla todas las recetas "
            "que lo usan a la vez."
        )
        catalogo = cargar_catalogo()
        por_alimento: dict[str, dict] = {}
        for r in cargar_recetas():
            for ing in r["ingredientes"]:
                if ing["alimento"] not in catalogo:
                    entry = por_alimento.setdefault(ing["alimento"], {"grupo": ing.get("grupo_smae"), "recetas": set()})
                    entry["recetas"].add(r["nombre"])

        if not por_alimento:
            st.success("Sin ingredientes huérfanos.")
            return

        total_recetas = len({nombre for info in por_alimento.values() for nombre in info["recetas"]})
        st.warning(f"{len(por_alimento)} alimento(s) sin catalogar, en {total_recetas} receta(s) en total.")
        for alimento, info in sorted(por_alimento.items()):
            with st.container(border=True):
                grupo_txt = GRUPO_ETIQUETA.get(info["grupo"], info["grupo"]) if info["grupo"] else "(libre)"
                st.markdown(f"**{alimento}** — grupo declarado: {grupo_txt}")
                st.caption("En: " + ", ".join(sorted(info["recetas"])))
                c1, c2 = st.columns([3, 1])
                cantidad = c1.text_input(
                    "Cantidad por equivalente", key=f"cant_huerfano_{alimento}",
                    placeholder="ej. 1/2 taza, 30 g", label_visibility="collapsed",
                )
                if c2.button("+ Catalogar", key=f"catalogar_{alimento}", disabled=not cantidad.strip()):
                    db().catalogo_alimentos.insert_one({
                        "alimento": alimento, "grupo": info["grupo"],
                        "cantidad_por_equivalente": cantidad.strip(),
                    })
                    invalidar_cache_catalogo()
                    st.session_state["_flash_config"] = f"'{alimento}' agregado al catálogo."
                    st.rerun()


def _check_recetas_huerfanas():
    with st.expander("🍽️ Referencias a recetas que ya no existen"):
        st.caption(
            "Los menús semanales y los días guardados guardan un `receta_id` -- si esa receta se "
            "elimina del banco, la referencia queda huérfana. Los días guardados de \"Menú del "
            "día\" son bitácora histórica y solo se muestran aquí (no se editan); los menús "
            "semanales sí se pueden limpiar directo."
        )
        recetas_ids = {r["receta_id"] for r in cargar_recetas()}

        problemas_plantillas = [
            (p, tiempo, r)
            for p in db().plantillas_semana.find({}, {"_id": 0})
            for tiempo, lista in p["tiempos"].items()
            for r in lista
            if r["receta_id"] not in recetas_ids
        ]
        problemas_dias = [
            (doc, tiempo, inst)
            for doc in db().menus_construidos.find({}, {"_id": 0})
            for tiempo, datos in doc.get("tiempos", {}).items()
            for inst in datos.get("seleccion", [])
            if inst["receta_id"] not in recetas_ids
        ]

        if not problemas_plantillas and not problemas_dias:
            st.success("Sin referencias huérfanas a recetas eliminadas.")
            return

        if problemas_plantillas:
            st.warning(f"{len(problemas_plantillas)} referencia(s) huérfana(s) en menús semanales.")
            for p, tiempo, r in problemas_plantillas:
                c1, c2 = st.columns([3, 1])
                c1.markdown(
                    f"**{r['nombre']}** _(eliminada)_ en menú **{p['nombre']}** "
                    f"({p['persona']}) — {TIEMPO_LABEL.get(tiempo, tiempo)}"
                )
                if c2.button("Quitar", key=f"quitar_huerfana_{p['persona']}_{p['nombre']}_{tiempo}_{r['receta_id']}"):
                    db().plantillas_semana.update_one(
                        {"persona": p["persona"], "nombre": p["nombre"]},
                        {"$pull": {f"tiempos.{tiempo}": {"receta_id": r["receta_id"]}}},
                    )
                    st.session_state["_flash_config"] = f"Referencia a '{r['nombre']}' quitada de '{p['nombre']}'."
                    st.rerun()

        if problemas_dias:
            st.info(f"{len(problemas_dias)} referencia(s) huérfana(s) en días guardados (histórico, no editable):")
            for doc, tiempo, inst in problemas_dias:
                st.caption(f"- {inst['nombre']} (eliminada) — {doc['persona']} / {doc['fecha']} / {TIEMPO_LABEL.get(tiempo, tiempo)}")


def _check_vector_desincronizado():
    with st.expander("🧮 Vector de equivalentes desincronizado en una receta"):
        st.caption(
            "El `vector_equivalentes` guardado debería ser siempre la suma de los ingredientes -- "
            "si no coincide, quedó de una edición directa en Mongo o un bug viejo."
        )
        problemas = []
        for r in cargar_recetas():
            real = sumar_por_grupo(r["ingredientes"], "grupo_smae", "equivalentes")
            if real != r.get("vector_equivalentes", {}):
                problemas.append((r, real))

        if not problemas:
            st.success("Todos los vectores coinciden con sus ingredientes.")
            return

        st.warning(f"{len(problemas)} receta(s) con vector desincronizado.")
        for r, real in problemas:
            with st.container(border=True):
                st.markdown(f"**{r['nombre']}**")
                st.markdown("Guardado: " + _chips(r.get("vector_equivalentes", {})), unsafe_allow_html=True)
                st.markdown("Real (según ingredientes): " + _chips(real), unsafe_allow_html=True)
                if st.button("Recalcular y guardar", key=f"recalc_{r['receta_id']}"):
                    db().recetas.update_one({"receta_id": r["receta_id"]}, {"$set": {"vector_equivalentes": real}})
                    invalidar_cache_recetas()
                    st.session_state["_flash_config"] = f"Vector de '{r['nombre']}' recalculado."
                    st.rerun()


def _check_duplicados_catalogo():
    with st.expander("🔎 Posibles duplicados en el catálogo de ingredientes"):
        st.caption(
            "Compara nombres por similitud (no exacta) -- ej. \"Aceite de oliva\" vs \"Aceite "
            "oliva\". No son necesariamente el mismo alimento: revisa cada par antes de fusionar "
            "(ver regla 9 de CLAUDE.md)."
        )
        nombres = sorted(cargar_catalogo().keys())
        pares = []
        for i, a in enumerate(nombres):
            norm_a = normalizar_busqueda(a)
            for b in nombres[i + 1:]:
                ratio = difflib.SequenceMatcher(None, norm_a, normalizar_busqueda(b)).ratio()
                if ratio >= 0.82:
                    pares.append((a, b, ratio))
        pares.sort(key=lambda x: -x[2])

        if not pares:
            st.success("Sin pares sospechosos.")
            return

        st.info(f"{len(pares)} par(es) parecido(s), el más parecido primero:")
        for a, b, ratio in pares[:30]:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{a}** ↔ **{b}** _(similitud {ratio:.0%})_")
            if c2.button("Fusionar", key=f"ir_fusionar_{a}_{b}"):
                st.session_state["_pendiente_ing_editar_selector"] = a
                st.switch_page("views/editor_ingredientes.py")


def _check_personas_sin_objetivo():
    with st.expander("🧑‍🤝‍🧑 Personas sin objetivo diario"):
        sin_objetivo = [p for p in cargar_personas() if not cargar_objetivo(p)]
        if not sin_objetivo:
            st.success("Todas las personas tienen un objetivo configurado.")
            return
        st.warning(f"Sin objetivo: {', '.join(sin_objetivo)}.")
        if st.button("Ir a Personas", key="ir_personas"):
            st.switch_page("views/personas.py")


def _check_asignacion_rota():
    with st.expander("🗓️ Asignación semanal apuntando a menús eliminados"):
        st.caption("Un día de la semana puede quedar apuntando a un menú que ya se eliminó.")
        problemas = []
        for doc in db().asignacion_semanal.find({}, {"_id": 0}):
            plantillas_persona = {
                p["nombre"] for p in db().plantillas_semana.find({"persona": doc["persona"]}, {"nombre": 1})
            }
            for dia, nombre in doc.get("dias", {}).items():
                if nombre and nombre not in plantillas_persona:
                    problemas.append((doc["persona"], dia, nombre))

        if not problemas:
            st.success("Sin referencias rotas en la asignación semanal.")
            return

        st.warning(f"{len(problemas)} día(s) apuntando a un menú eliminado.")
        for persona, dia, nombre in problemas:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{persona}** — {dia.capitalize()}: '{nombre}' _(eliminado)_")
            if c2.button("Marcar como libre", key=f"limpiar_asig_{persona}_{dia}"):
                db().asignacion_semanal.update_one({"persona": persona}, {"$set": {f"dias.{dia}": None}})
                st.session_state["_flash_config"] = f"{dia.capitalize()} de {persona} marcado como libre."
                st.rerun()


def render() -> None:
    st.title("⚙️ Configuración")
    st.caption("Herramientas de administración -- no es para el uso diario de la app.")

    if "_flash_config" in st.session_state:
        st.success(st.session_state.pop("_flash_config"))

    st.header("Buscar relaciones")
    st.caption("Para inspeccionar a mano antes de decidir si algo necesita corregirse.")
    col_a, col_b = st.columns(2)
    with col_a:
        _buscar_recetas_de_ingrediente()
    with col_b:
        _buscar_uso_de_receta()

    st.divider()
    st.header("Chequeos automáticos")
    st.caption(
        "Cada uno es independiente -- revisa una sola relación entre colecciones. Mongo no las "
        "valida solo (son referencias por nombre/id, no llaves foráneas), así que nada más avisa "
        "cuando una se rompe."
    )
    _check_ingredientes_huerfanos()
    _check_recetas_huerfanas()
    _check_vector_desincronizado()
    _check_duplicados_catalogo()
    _check_personas_sin_objetivo()
    _check_asignacion_rota()


render()
