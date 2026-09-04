"""EquiVale — "Configuración": panel de administración que no encaja en las páginas de uso
diario. Por ahora trae "Integridad de datos" -- Mongo no valida las relaciones entre colecciones
(son referencias por nombre/id sueltas, no llaves foráneas: un `ingrediente.alimento` que apunta
a `catalogo_alimentos`, un `receta_id` que apunta a `recetas`, etc.), así que nada avisa cuando
una de esas referencias se rompe (se elimina el alimento/receta del lado "dueño" pero no se
actualiza quien lo usaba). Esta página junta herramientas de búsqueda ("¿dónde se usa X?") y
chequeos automáticos ("¿qué referencias ya están rotas?"), cada uno independiente.

Ver UI-BUILD-YOUR-MENU.md -> "Configuración" para la especificación completa.
"""

import streamlit as st

from nutriguia import chequeos
from nutriguia import db as bd
from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import (
    cargar_catalogo,
    cargar_recetas,
    db,
    invalidar_cache_catalogo,
    invalidar_cache_recetas,
)
from nutriguia.validation import (
    corregir_alimentos_libres_en_cero,
    fusionar_duplicados_en_menu_guardado,
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
    for receta in bd.buscar_recetas_con_ingrediente(db(), nombre_viejo):
        ingredientes = receta["ingredientes"]
        cambio = False
        for ing in ingredientes:
            if ing["alimento"] == nombre_viejo:
                ing["alimento"] = nombre_nuevo
                cambio = True
        if cambio:
            ingredientes = fusionar_ingredientes_duplicados(ingredientes)
            vector = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
            receta["ingredientes"] = ingredientes
            receta["vector_equivalentes"] = vector
            bd.guardar_receta(db(), receta)
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
    for documento in bd.listar_todos_los_dias(db()):
        if renombrar_ingrediente_en_menu_guardado(documento, nombre_viejo, nombre_nuevo):
            bd.guardar_dia(
                db(), documento["persona"], documento["fecha"], documento.get("nombre"), documento
            )
            tocados += 1
    return tocados


# ---------------------------------------------------------------------------
# Sección A: buscar relaciones (lookup manual)
# ---------------------------------------------------------------------------

def _buscar_recetas_de_ingrediente():
    st.subheader("¿Dónde se usa un ingrediente?")
    catalogo = cargar_catalogo()
    recetas = cargar_recetas()
    nombres = [SIN_SELECCION] + sorted(catalogo.keys())
    elegido = _selectbox_seguro("Ingrediente", nombres, key="config_buscar_ingrediente")
    if elegido == SIN_SELECCION:
        return

    usos = [r for r in recetas if any(ing["alimento"] == elegido for ing in r["ingredientes"])]
    # También en días ya guardados (2026-08-31, a pedido del usuario: tras corregir "Pasta
    # cocida" en el catálogo, quería poder revisar dónde se usa para confirmar que el valor nuevo
    # aplica bien) -- una receta se puede corregir en el banco sin que eso toque los días que ya
    # se guardaron con su versión anterior (ver BUG-013), y un ingrediente suelto (FR-007) nunca
    # vive en `recetas`, solo aquí -- la búsqueda de recetas sola no lo encontraría.
    en_dias = [
        (doc, tiempo, inst, ing)
        for doc, tiempo, indice, inst, ing in bd.buscar_dias_con_ingrediente(db(), elegido)
    ]

    if not usos and not en_dias:
        st.caption(f"'{elegido}' no se usa en ninguna receta ni día guardado todavía.")
        return

    if usos:
        st.caption(f"En {len(usos)} receta(s) del banco:")
        for r in usos:
            ing = next(i for i in r["ingredientes"] if i["alimento"] == elegido)
            etiquetas = []
            if ing.get("bloqueado"):
                etiquetas.append("bloqueado")
            if ing.get("opcional"):
                etiquetas.append("opcional")
            sufijo = f" _({', '.join(etiquetas)})_" if etiquetas else ""
            st.markdown(f"- **{r['nombre']}** — {ing['equivalentes']} equivalente(s){sufijo}")

    if en_dias:
        st.caption(f"En {len(en_dias)} día(s) ya guardado(s):")
        for doc, tiempo, inst, ing in en_dias:
            etiqueta_dia = f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}"
            origen = inst["nombre"] if inst.get("receta_id") else f"{inst['nombre']} (suelto)"
            st.markdown(
                f"- {etiqueta_dia} — {TIEMPO_LABEL.get(tiempo, tiempo)} — **{origen}** — "
                f"{ing['equivalentes']} equivalente(s)"
            )


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

    dias = bd.listar_todos_los_dias(db())
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
        por_alimento = chequeos.ingredientes_huerfanos()

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
                    bd.guardar_alimento(db(), {
                        "alimento": alimento, "grupo": info["grupo"],
                        "cantidad_por_equivalente": cantidad.strip(),
                    })
                    invalidar_cache_catalogo()
                    chequeos.invalidar_cache_alertas()
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
                    chequeos.invalidar_cache_alertas()
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
        problemas_dias = chequeos.recetas_huerfanas()

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
        problemas = chequeos.vectores_desincronizados()

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
                    r["vector_equivalentes"] = real
                    bd.guardar_receta(db(), r)
                    invalidar_cache_recetas()
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Vector de '{r['nombre']}' recalculado."
                    st.rerun()


def _check_ingredientes_duplicados_en_receta():
    with st.expander("🔁 Ingredientes duplicados dentro de una misma receta o día guardado"):
        st.caption(
            "El mismo alimento listado dos o más veces en una receta (o dentro de un día ya "
            "guardado de \"Menú del día\") -- suele pasar al usar \"🔗 Usar este\" (arriba) cuando "
            "ya había un ingrediente con ese nombre (BUG-009, corregido para que ya no vuelva a "
            "pasar en el banco de recetas), o cuando el día se guardó ANTES de esa corrección y "
            "nunca se volvió a abrir (2026-08-31, ver BUG-013). A diferencia del chequeo de "
            "duplicados del catálogo, aquí no hay ambigüedad -- es el mismo nombre exacto, así que "
            "fusionar (sumar sus equivalentes en una sola fila) es seguro con un clic."
        )
        problemas_recetas = chequeos.ingredientes_duplicados_en_recetas()
        problemas_dias = chequeos.ingredientes_duplicados_en_dias()

        if not problemas_recetas and not problemas_dias:
            st.success("Sin ingredientes duplicados dentro de una receta o día guardado.")
            return

        st.warning(
            f"{len(problemas_recetas)} receta(s) y {len(problemas_dias)} día(s) guardado(s) con "
            "algún ingrediente repetido."
        )
        for r, repetidos in problemas_recetas:
            with st.container(border=True):
                st.markdown(f"**{r['nombre']}** (receta del banco) — repetido: " + ", ".join(f"'{n}'" for n in repetidos))
                if st.button("Fusionar", key=f"fusionar_dup_{r['receta_id']}"):
                    ingredientes = fusionar_ingredientes_duplicados(r["ingredientes"])
                    vector = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
                    r["ingredientes"] = ingredientes
                    r["vector_equivalentes"] = vector
                    bd.guardar_receta(db(), r)
                    invalidar_cache_recetas()
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Ingredientes duplicados de '{r['nombre']}' fusionados."
                    st.rerun()
        for doc, tiempo, indice, inst, repetidos in problemas_dias:
            with st.container(border=True):
                etiqueta_dia = f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}"
                st.markdown(
                    f"**{inst['nombre']}** (día guardado: {etiqueta_dia}, {TIEMPO_LABEL.get(tiempo, tiempo)}) "
                    "— repetido: " + ", ".join(f"'{n}'" for n in repetidos)
                )
                if st.button("Fusionar", key=f"fusionar_dup_dia_{doc['persona']}_{doc['fecha']}_{tiempo}_{indice}"):
                    fusionar_duplicados_en_menu_guardado(doc, tiempo, indice)
                    bd.guardar_dia(db(), doc["persona"], doc["fecha"], doc.get("nombre"), doc)
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Ingredientes duplicados de '{inst['nombre']}' fusionados."
                    st.rerun()


def _check_ingredientes_libres_en_cero():
    with st.expander("🧂 Ingredientes libres con cantidad en cero"):
        st.caption(
            "Un ingrediente sin grupo SMAE (ej. una especia, \"al gusto\") con `equivalentes: 0` "
            "no afecta la aritmética de equivalentes por grupo (nunca contó para ninguno), pero "
            "\"Lista del súper\"/\"Menú semanal\" sí usan ese número para escalar cuánto mostrar "
            "de ese alimento -- un 0 ahí se ve como \"0 cucharadita\" en una lista de compras real "
            "(KC-003 en BUGS.md, detectado 2026-09-04 tras una semana de uso). Corregir pone el "
            "mínimo sensible (1 -- \"aparece una vez\") sin tocar nada más de la receta/día."
        )
        problemas_recetas = chequeos.ingredientes_libres_en_cero_en_recetas()
        problemas_dias = chequeos.ingredientes_libres_en_cero_en_dias()

        if not problemas_recetas and not problemas_dias:
            st.success("Sin ingredientes libres en cero.")
            return

        st.warning(
            f"{len(problemas_recetas)} receta(s) y {len(problemas_dias)} día(s) guardado(s) con "
            "algún ingrediente libre en cero."
        )
        for r, afectados in problemas_recetas:
            with st.container(border=True):
                st.markdown(f"**{r['nombre']}** (receta del banco) — en cero: " + ", ".join(f"'{n}'" for n in afectados))
                if st.button("Corregir a 1", key=f"corregir_libre_cero_{r['receta_id']}"):
                    r["ingredientes"] = corregir_alimentos_libres_en_cero(r["ingredientes"])
                    bd.guardar_receta(db(), r)
                    invalidar_cache_recetas()
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Ingredientes libres de '{r['nombre']}' corregidos a 1."
                    st.rerun()
        for doc, tiempo, indice, inst, afectados in problemas_dias:
            with st.container(border=True):
                etiqueta_dia = f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}"
                st.markdown(
                    f"**{inst['nombre']}** (día guardado: {etiqueta_dia}, {TIEMPO_LABEL.get(tiempo, tiempo)}) "
                    "— en cero: " + ", ".join(f"'{n}'" for n in afectados)
                )
                if st.button("Corregir a 1", key=f"corregir_libre_cero_dia_{doc['persona']}_{doc['fecha']}_{tiempo}_{indice}"):
                    inst["ingredientes"] = corregir_alimentos_libres_en_cero(inst["ingredientes"])
                    bd.guardar_dia(db(), doc["persona"], doc["fecha"], doc.get("nombre"), doc)
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Ingredientes libres de '{inst['nombre']}' corregidos a 1."
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
        pares = chequeos.pares_similares_en_catalogo()

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
                    bd.descartar_par(db(), a, b)
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"'{a}' y '{b}' marcados como diferentes -- no se vuelven a sugerir."
                    st.rerun()

        descartados_pares = sorted(bd.listar_pares_descartados(db()))
        if descartados_pares:
            with st.expander(f"Pares marcados como diferentes ({len(descartados_pares)})"):
                for a, b in descartados_pares:
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"{a} ↔ {b}")
                    if c2.button("Deshacer", key=f"deshacer_desc_{a}_{b}"):
                        bd.deshacer_descarte(db(), a, b)
                        chequeos.invalidar_cache_alertas()
                        st.session_state["_flash_config"] = f"Se vuelve a sugerir: {a} ↔ {b}."
                        st.rerun()


def _check_personas_sin_objetivo():
    with st.expander("🧑‍🤝‍🧑 Personas sin objetivo diario"):
        sin_objetivo = chequeos.personas_sin_objetivo()
        if not sin_objetivo:
            st.success("Todas las personas tienen un objetivo configurado.")
            return
        st.warning(f"Sin objetivo: {', '.join(sin_objetivo)}.")
        if st.button("Ir a Personas", key="ir_personas"):
            st.switch_page("views/personas.py")


def _check_asignacion_rota():
    with st.expander("🗓️ Asignación semanal apuntando a menús eliminados"):
        st.caption("Un día de la semana puede quedar apuntando a un menú que ya se eliminó.")
        problemas = chequeos.asignacion_rota()

        if not problemas:
            st.success("Sin referencias rotas en la asignación semanal.")
            return

        st.warning(f"{len(problemas)} día(s) apuntando a un menú eliminado.")
        for persona, dia, nombre in problemas:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{persona}** — {dia.capitalize()}: '{nombre}' _(eliminado)_")
            if c2.button("Marcar como libre", key=f"limpiar_asig_{persona}_{dia}"):
                asignacion = bd.obtener_asignacion(db(), persona)
                dias_dict = asignacion.get("dias", {}) if asignacion else {}
                dias_dict[dia] = None
                bd.guardar_asignacion(db(), persona, dias_dict)
                chequeos.invalidar_cache_alertas()
                st.session_state["_flash_config"] = f"{dia.capitalize()} de {persona} marcado como libre."
                st.rerun()


def _check_dias_con_estado_desactualizado():
    with st.expander("🔄 Días guardados con estado desactualizado"):
        st.caption(
            "El `estado`/delta de un día ya guardado se calcula UNA vez, al guardarlo -- si el "
            "criterio para decidir qué cuenta como \"completo\" cambia después (2026-08-31, ver "
            "CLAUDE.md: Cereal/Leguminosa intercambiables desde la v0.26.0) y ese día no se vuelve "
            "a abrir/guardar, se queda mostrando lo viejo en el historial. Recalcular aquí no "
            "cambia ningún ingrediente, solo pone al día `actual_diario`/`delta_diario`/`estado`."
        )
        problemas = chequeos.dias_con_estado_desactualizado()

        if not problemas:
            st.success("El estado de todos los días guardados coincide con lo que se recalcula hoy.")
            return

        st.warning(f"{len(problemas)} día(s) guardado(s) con estado desactualizado.")
        for doc, delta_nuevo, estado_nuevo in problemas:
            with st.container(border=True):
                etiqueta = f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}"
                st.markdown(
                    f"**{etiqueta}** — guardado: `{doc.get('estado')}` -> recalculado: `{estado_nuevo}`"
                )
                st.markdown("Delta guardado: " + _chips(doc.get("delta_diario", {})), unsafe_allow_html=True)
                st.markdown("Delta recalculado: " + _chips(delta_nuevo), unsafe_allow_html=True)
                if st.button("Recalcular y guardar", key=f"recalc_estado_{doc['persona']}_{doc['fecha']}"):
                    doc["delta_diario"] = delta_nuevo
                    doc["estado"] = estado_nuevo
                    bd.guardar_dia(db(), doc["persona"], doc["fecha"], doc.get("nombre"), doc)
                    chequeos.invalidar_cache_alertas()
                    st.session_state["_flash_config"] = f"Estado de '{etiqueta}' recalculado a '{estado_nuevo}'."
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
        "Cada uno revisa una sola cosa, de forma independiente. El badge junto a \"Configuración\" "
        "en la barra lateral avisa cuántos tienen algo que revisar, para no tener que abrir esta "
        "página solo para chequear."
    )
    _check_ingredientes_huerfanos()
    _check_recetas_huerfanas()
    _check_vector_desincronizado()
    _check_ingredientes_duplicados_en_receta()
    _check_ingredientes_libres_en_cero()
    _check_duplicados_catalogo()
    _check_personas_sin_objetivo()
    _check_asignacion_rota()
    _check_dias_con_estado_desactualizado()


render()
