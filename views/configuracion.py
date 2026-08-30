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
from nutriguia.validation import (
    fusionar_ingredientes_duplicados,
    renombrar_ingrediente_en_menu_guardado,
    sumar_por_grupo,
)

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


def _renombrar_en_recetas(nombre_viejo: str, nombre_nuevo: str) -> int:
    """Mismo mecanismo que en editor_ingredientes.py: las recetas referencian un alimento por
    nombre, no por id -- reemplazar acá evita dejar una receta apuntando a un nombre que ya no
    existe en ningún lado (ni el orfanado ni uno nuevo). Fusiona con `fusionar_ingredientes_
    duplicados()` por si la receta YA tenía un ingrediente con el nombre nuevo -- si no, quedaban
    dos filas con el mismo `alimento` en vez de una sola (BUG-009 en BUGS.md, detectado
    2026-08-30)."""
    tocadas = 0
    for receta in db().recetas.find({"ingredientes.alimento": nombre_viejo}):
        ingredientes = receta["ingredientes"]
        cambio = False
        for ing in ingredientes:
            if ing["alimento"] == nombre_viejo:
                ing["alimento"] = nombre_nuevo
                cambio = True
        if cambio:
            ingredientes = fusionar_ingredientes_duplicados(ingredientes)
            vector = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
            db().recetas.update_one(
                {"receta_id": receta["receta_id"]},
                {"$set": {"ingredientes": ingredientes, "vector_equivalentes": vector}},
            )
            tocadas += 1
    if tocadas:
        invalidar_cache_recetas()
    return tocadas


def _renombrar_en_menus_construidos(nombre_viejo: str, nombre_nuevo: str) -> int:
    """Cascada de `_renombrar_en_recetas()` hacia `menus_construidos` -- un día ya guardado es un
    snapshot completo (ver schema.md), no una referencia viva al banco, así que renombrar solo en
    `recetas` no lo alcanza: el nombre viejo queda huérfano para siempre en cualquier día ya
    guardado que lo usara, aunque el banco ya esté limpio (BUG-013, detectado 2026-08-30 -- "Lista
    del súper" mostraba "Leche"/"Leche semi" huérfanas como "Sin grupo / libre" en vez de AOA)."""
    tocados = 0
    for documento in db().menus_construidos.find({}):
        if renombrar_ingrediente_en_menu_guardado(documento, nombre_viejo, nombre_nuevo):
            db().menus_construidos.update_one(
                {"persona": documento["persona"], "fecha": documento["fecha"]},
                {
                    "$set": {
                        "tiempos": documento["tiempos"],
                        "actual_diario": documento["actual_diario"],
                        "delta_diario": documento["delta_diario"],
                        "estado": documento["estado"],
                    }
                },
            )
            tocados += 1
    return tocados


def _normalizar_par(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _pares_descartados() -> set[tuple[str, str]]:
    return {_normalizar_par(d["a"], d["b"]) for d in db().duplicados_descartados.find({}, {"_id": 0})}


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
        (doc["persona"], doc["fecha"], doc.get("nombre"), tiempo)
        for doc in dias
        for tiempo, datos in doc.get("tiempos", {}).items()
        if any(inst["receta_id"] == elegido for inst in datos.get("seleccion", []))
    ]

    if not en_dias:
        st.caption("No aparece en ningún día guardado todavía.")
        return
    st.caption(f"En {len(en_dias)} día(s) guardado(s) de 'Menú del día':")
    for persona, fecha, nombre, tiempo in en_dias:
        etiqueta_nombre = f" — **{nombre}**" if nombre else ""
        st.markdown(f"- {persona} — {fecha}{etiqueta_nombre} — {TIEMPO_LABEL.get(tiempo, tiempo)}")


# ---------------------------------------------------------------------------
# Sección B: chequeos automáticos (solo muestran problemas, no listas completas)
# ---------------------------------------------------------------------------

def _check_ingredientes_huerfanos():
    with st.expander("🥕 Ingredientes que ya no están en el catálogo", expanded=True):
        st.caption(
            "Una receta (o un día ya guardado de \"Menú del día\") guarda cada ingrediente por "
            "nombre -- si ese alimento se elimina del catálogo (o nunca se catalogó), el "
            "ingrediente se vuelve \"no ajustable\" en la UI y aparece como \"Sin grupo / libre\" "
            "en \"Lista del súper\" en vez de su grupo real, pero puede pasar desapercibido. "
            "Catalogarlo aquí lo arregla en todos lados a la vez."
        )
        catalogo = cargar_catalogo()
        por_alimento: dict[str, dict] = {}
        for r in cargar_recetas():
            for ing in r["ingredientes"]:
                if ing["alimento"] not in catalogo:
                    entry = por_alimento.setdefault(
                        ing["alimento"], {"grupo": ing.get("grupo_smae"), "recetas": set(), "dias": set()}
                    )
                    entry["recetas"].add(r["nombre"])
        # BUG-013 (2026-08-30): un día ya guardado es un snapshot completo, no una referencia viva
        # al banco de recetas -- limpiar/renombrar en `recetas` no lo alcanza, así que un alimento
        # puede quedar huérfano SOLO en `menus_construidos` (el banco ya limpio no lo delata).
        for doc in db().menus_construidos.find({}):
            for tiempo, datos in doc.get("tiempos", {}).items():
                for inst in datos.get("seleccion", []):
                    for ing in inst["ingredientes"]:
                        if ing["alimento"] not in catalogo:
                            entry = por_alimento.setdefault(
                                ing["alimento"], {"grupo": ing.get("grupo_smae"), "recetas": set(), "dias": set()}
                            )
                            etiqueta_dia = f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}"
                            entry["dias"].add(etiqueta_dia)

        if not por_alimento:
            st.success("Sin ingredientes huérfanos.")
            return

        total_usos = sum(len(info["recetas"]) + len(info["dias"]) for info in por_alimento.values())
        st.warning(f"{len(por_alimento)} alimento(s) sin catalogar, en {total_usos} lugar(es) en total.")
        opciones_existentes = [SIN_SELECCION] + sorted(catalogo.keys())
        for alimento, info in sorted(por_alimento.items()):
            with st.container(border=True):
                grupo_txt = GRUPO_ETIQUETA.get(info["grupo"], info["grupo"]) if info["grupo"] else "(libre)"
                st.markdown(f"**{alimento}** — grupo declarado: {grupo_txt}")
                if info["recetas"]:
                    st.caption("En recetas: " + ", ".join(sorted(info["recetas"])))
                if info["dias"]:
                    st.caption("En días ya guardados: " + ", ".join(sorted(info["dias"])))

                st.caption("Opción A — catalogarlo como alimento nuevo:")
                c1, c2 = st.columns([3, 1])
                cantidad = c1.text_input(
                    "Cantidad por equivalente", key=f"cant_huerfano_{alimento}",
                    placeholder="ej. 1/2 taza, 30 g", label_visibility="collapsed",
                )
                if c2.button("+ Catalogar nuevo", key=f"catalogar_{alimento}", disabled=not cantidad.strip()):
                    db().catalogo_alimentos.insert_one({
                        "alimento": alimento, "grupo": info["grupo"],
                        "cantidad_por_equivalente": cantidad.strip(),
                    })
                    invalidar_cache_catalogo()
                    st.session_state["_flash_config"] = f"'{alimento}' agregado al catálogo."
                    st.rerun()

                st.caption("Opción B — ya es lo mismo que un alimento que ya tienes catalogado:")
                c3, c4 = st.columns([3, 1])
                elegido_existente = c3.selectbox(
                    "Reemplazar por", opciones_existentes, key=f"reemplazar_sel_{alimento}",
                    label_visibility="collapsed",
                )
                if c4.button(
                    "🔗 Usar este", key=f"reemplazar_btn_{alimento}",
                    disabled=elegido_existente == SIN_SELECCION,
                ):
                    tocadas_recetas = _renombrar_en_recetas(alimento, elegido_existente)
                    tocados_dias = _renombrar_en_menus_construidos(alimento, elegido_existente)
                    partes = []
                    if tocadas_recetas:
                        partes.append(f"{tocadas_recetas} receta(s)")
                    if tocados_dias:
                        partes.append(f"{tocados_dias} día(s) ya guardado(s)")
                    detalle = " y ".join(partes) if partes else "0 lugares"
                    st.session_state["_flash_config"] = (
                        f"'{alimento}' reemplazado por '{elegido_existente}' en {detalle}."
                    )
                    st.rerun()


def _check_recetas_huerfanas():
    with st.expander("🍽️ Referencias a recetas que ya no existen"):
        st.caption(
            "Cada día guardado de \"Menú del día\" (con nombre o sin él) guarda un `receta_id` "
            "por cada receta elegida -- si esa receta se elimina del banco, la referencia queda "
            "huérfana. Se corrige abriendo ese día desde \"Menú del día\" y quitando el "
            "ingrediente ahí, no desde aquí."
        )
        recetas_ids = {r["receta_id"] for r in cargar_recetas()}
        problemas_dias = [
            (doc, tiempo, inst)
            for doc in db().menus_construidos.find({}, {"_id": 0})
            for tiempo, datos in doc.get("tiempos", {}).items()
            for inst in datos.get("seleccion", [])
            # `receta_id: None` = ingrediente suelto (FR-007), no una receta del banco -- no es
            # una referencia rota, es la forma normal de un ingrediente sin receta.
            if inst["receta_id"] is not None and inst["receta_id"] not in recetas_ids
        ]

        if not problemas_dias:
            st.success("Sin referencias huérfanas a recetas eliminadas.")
            return

        st.warning(f"{len(problemas_dias)} referencia(s) huérfana(s) en días guardados:")
        for doc, tiempo, inst in problemas_dias:
            etiqueta_nombre = f" — **{doc['nombre']}**" if doc.get("nombre") else ""
            st.caption(
                f"- {inst['nombre']} (eliminada) — {doc['persona']} / {doc['fecha']}"
                f"{etiqueta_nombre} / {TIEMPO_LABEL.get(tiempo, tiempo)}"
            )


def _check_vector_desincronizado():
    with st.expander("🧮 Vector de equivalentes desincronizado en una receta"):
        st.caption(
            "Los equivalentes guardados de una receta deberían ser siempre la suma de sus "
            "ingredientes -- si no coincide, quedó de una edición manual o un bug viejo."
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


def _check_ingredientes_duplicados_en_receta():
    with st.expander("🔁 Ingredientes duplicados dentro de una misma receta"):
        st.caption(
            "El mismo alimento listado dos o más veces en una receta -- suele pasar al usar "
            "\"🔗 Usar este\" (arriba) cuando la receta YA tenía un ingrediente con ese nombre "
            "(BUG-009, corregido para que ya no vuelva a pasar). A diferencia del chequeo de "
            "duplicados del catálogo, aquí no hay ambigüedad -- son el mismo nombre exacto dentro "
            "de la misma receta, así que fusionar (sumar sus equivalentes en una sola fila) es "
            "seguro con un clic."
        )
        problemas = []
        for r in cargar_recetas():
            vistos: dict[str, int] = {}
            for ing in r["ingredientes"]:
                vistos[ing["alimento"]] = vistos.get(ing["alimento"], 0) + 1
            repetidos = sorted(n for n, veces in vistos.items() if veces > 1)
            if repetidos:
                problemas.append((r, repetidos))

        if not problemas:
            st.success("Sin ingredientes duplicados dentro de una receta.")
            return

        st.warning(f"{len(problemas)} receta(s) con algún ingrediente repetido.")
        for r, repetidos in problemas:
            with st.container(border=True):
                st.markdown(f"**{r['nombre']}** — repetido: " + ", ".join(f"'{n}'" for n in repetidos))
                if st.button("Fusionar", key=f"fusionar_dup_{r['receta_id']}"):
                    ingredientes = fusionar_ingredientes_duplicados(r["ingredientes"])
                    vector = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
                    db().recetas.update_one(
                        {"receta_id": r["receta_id"]},
                        {"$set": {"ingredientes": ingredientes, "vector_equivalentes": vector}},
                    )
                    invalidar_cache_recetas()
                    st.session_state["_flash_config"] = f"Ingredientes duplicados de '{r['nombre']}' fusionados."
                    st.rerun()


def _check_duplicados_catalogo():
    with st.expander("🔎 Posibles duplicados en el catálogo de ingredientes"):
        st.caption(
            "Compara nombres por similitud de texto (no exacta -- sin regex ni IA, solo "
            "`difflib` comparando letra por letra), ej. \"Aceite de oliva\" vs \"Aceite oliva\". "
            "No son necesariamente el mismo alimento: revisa cada par antes de fusionar (ver "
            "regla 9 de CLAUDE.md). Ojo con la cantidad por equivalente de cada lado -- fusionar "
            "no ajusta los equivalentes ya guardados en recetas, así que si de verdad es el "
            "mismo alimento pero con medidas distintas, revisa esas recetas después de fusionar."
        )
        catalogo = cargar_catalogo()
        nombres = sorted(catalogo.keys())
        descartados = _pares_descartados()
        pares = []
        for i, a in enumerate(nombres):
            norm_a = normalizar_busqueda(a)
            for b in nombres[i + 1:]:
                if _normalizar_par(a, b) in descartados:
                    continue
                ratio = difflib.SequenceMatcher(None, norm_a, normalizar_busqueda(b)).ratio()
                if ratio >= 0.82:
                    pares.append((a, b, ratio))
        pares.sort(key=lambda x: -x[2])

        if not pares:
            st.success("Sin pares sospechosos.")
        else:
            st.info(f"{len(pares)} par(es) parecido(s), el más parecido primero:")
            for a, b, ratio in pares[:30]:
                cant_a = catalogo[a]["cantidad_por_equivalente"]
                cant_b = catalogo[b]["cantidad_por_equivalente"]
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(
                    f"**{a}** _( {cant_a} )_ ↔ **{b}** _( {cant_b} )_ — similitud {ratio:.0%}"
                )
                if c2.button("Fusionar", key=f"ir_fusionar_{a}_{b}"):
                    st.session_state["_pendiente_ing_editar_selector"] = a
                    st.switch_page("views/editor_ingredientes.py")
                if c3.button("Son diferentes", key=f"descartar_{a}_{b}"):
                    x, y = _normalizar_par(a, b)
                    db().duplicados_descartados.create_index([("a", 1), ("b", 1)], unique=True)
                    db().duplicados_descartados.update_one(
                        {"a": x, "b": y}, {"$setOnInsert": {"a": x, "b": y}}, upsert=True
                    )
                    st.session_state["_flash_config"] = f"'{a}' y '{b}' marcados como diferentes -- no se vuelven a sugerir."
                    st.rerun()

        descartados_docs = list(db().duplicados_descartados.find({}, {"_id": 0}))
        if descartados_docs:
            with st.expander(f"Pares marcados como diferentes ({len(descartados_docs)})"):
                for d in descartados_docs:
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"{d['a']} ↔ {d['b']}")
                    if c2.button("Deshacer", key=f"deshacer_desc_{d['a']}_{d['b']}"):
                        db().duplicados_descartados.delete_one({"a": d["a"], "b": d["b"]})
                        st.session_state["_flash_config"] = f"Se vuelve a sugerir: {d['a']} ↔ {d['b']}."
                        st.rerun()


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
            nombres_persona = {
                m["nombre"]
                for m in db().menus_construidos.find(
                    {"persona": doc["persona"], "nombre": {"$ne": None}}, {"nombre": 1}
                )
            }
            for dia, nombre in doc.get("dias", {}).items():
                if nombre and nombre not in nombres_persona:
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
        "Cada uno revisa una sola cosa, de forma independiente. Nada los corre automáticamente "
        "por su cuenta, así que si algo se desordena en otra parte de la app puede no notarse "
        "hasta que se abre esta página."
    )
    _check_ingredientes_huerfanos()
    _check_recetas_huerfanas()
    _check_vector_desincronizado()
    _check_ingredientes_duplicados_en_receta()
    _check_duplicados_catalogo()
    _check_personas_sin_objetivo()
    _check_asignacion_rota()


render()
