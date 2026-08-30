"""EquiVale — "Lista del súper" (FR-004, 2026-08-30, a pedido del usuario): suma los ingredientes
reales de la semana ya asignada en "Menú semanal" (uno o varios días con nombre, por persona) en
una lista consolidada de compras, agrupada por grupo SMAE. Soporta elegir **más de una persona a
la vez** (dos personas que viven juntas y hacen un solo súper -- actualización pedida el mismo
2026-08-30) -- el mismo alimento de ambas se suma en una sola línea, no dos separadas.

Página de solo lectura sobre lo que ya existe en `asignacion_semanal` + `menus_construidos` -- no
arma ni edita nada (eso sigue siendo trabajo de "Menú del día"/"Menú semanal"). Si un menú aplica
a varios días de la semana, sus ingredientes cuentan una vez POR DÍA que aplica -- es la cantidad
real que hay que comprar para toda la semana, no solo una porción del menú.

Ver UI-BUILD-YOUR-MENU.md → "Lista del súper" para la especificación completa.
"""

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.html_lista_super import SIN_CATALOGAR, agrupar_alimentos_por_grupo, generar_html_lista_super
from nutriguia.streamlit_data import cargar_catalogo, cargar_personas, db
from nutriguia.validation import sumar_por_grupo

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIA_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}


def _cargar_asignacion(persona: str) -> dict[str, str | None]:
    doc = db().asignacion_semanal.find_one({"persona": persona}, {"_id": 0})
    dias_guardados = doc.get("dias", {}) if doc else {}
    return {d: dias_guardados.get(d) for d in DIAS}


def _cargar_menus_nombrados(persona: str) -> dict[str, dict]:
    docs = db().menus_construidos.find({"persona": persona, "nombre": {"$ne": None}}, {"_id": 0})
    return {d["nombre"]: d for d in docs}


def _ingredientes_de_la_semana(persona: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Una ocurrencia de cada ingrediente incluido, por cada DÍA de la semana que use ese menú --
    si "Menú 1" aplica a lunes/miércoles/viernes, sus ingredientes cuentan 3 veces. Devuelve
    también los `(dia, nombre)` con referencia rota (nombre asignado que ya no existe en
    `menus_construidos`) para poder avisar -- mismo criterio de "detectar, no arreglar solo" que
    Configuración/"Menú semanal"."""
    asignacion = _cargar_asignacion(persona)
    menus_por_nombre = _cargar_menus_nombrados(persona)
    ingredientes: list[dict] = []
    rotos: list[tuple[str, str]] = []
    for dia in DIAS:
        nombre = asignacion.get(dia)
        if nombre is None:
            continue
        menu = menus_por_nombre.get(nombre)
        if menu is None:
            rotos.append((dia, nombre))
            continue
        for datos_tiempo in menu.get("tiempos", {}).values():
            for inst in datos_tiempo.get("seleccion", []):
                ingredientes.extend(ing for ing in inst["ingredientes"] if ing.get("incluido", True))
    return ingredientes, rotos


def render() -> None:
    st.title("🛒 EquiVale — Lista del súper")
    st.caption(
        "Suma los ingredientes reales de la semana ya asignada en \"Menú semanal\" en una lista "
        "consolidada de compras, agrupada por grupo SMAE."
    )

    personas = cargar_personas()
    seleccion = st.multiselect(
        "Persona(s)", personas, default=personas[:1] if personas else [],
        help="Elige más de una si viven juntas y hacen un solo súper -- el mismo alimento de "
             "ambas se suma en una sola línea, no dos separadas.",
    )
    if not seleccion:
        st.info("Elige al menos una persona.")
        return

    ingredientes_totales: list[dict] = []
    notas: list[str] = []
    for persona in seleccion:
        ingredientes, rotos = _ingredientes_de_la_semana(persona)
        ingredientes_totales.extend(ingredientes)
        if rotos:
            detalle = ", ".join(f"{DIA_LABEL[d]} ('{n}' ya no existe)" for d, n in rotos)
            notas.append(f"{persona}: referencias rotas en Menú semanal -- revisar ahí -- {detalle}.")

    if not ingredientes_totales:
        st.info(
            "Ninguna de las personas elegidas tiene días asignados en \"Menú semanal\" todavía."
        )
        st.page_link("views/menu_semanal.py", label="Ir a Menú semanal", icon="🗓️")
        return

    for n in notas:
        st.warning(n)

    catalogo = cargar_catalogo()
    resumen_por_alimento = sumar_por_grupo(ingredientes_totales, "alimento", "equivalentes")
    st.success(f"{len(resumen_por_alimento)} alimento(s) distinto(s) en la lista.")

    st.download_button(
        "🖨️ Descargar HTML para imprimir",
        data=generar_html_lista_super(seleccion, resumen_por_alimento, catalogo, notas),
        file_name="lista-del-super.html",
        mime="text/html",
        help="Ábrelo en tu navegador y usa Ctrl/Cmd+P para imprimirlo o guardarlo como PDF.",
    )

    st.divider()

    # Vista previa en pantalla, agrupada igual que el HTML descargable -- misma función
    # (`agrupar_alimentos_por_grupo()`) para no mantener dos criterios de agrupación en paralelo.
    for grupo, items in agrupar_alimentos_por_grupo(resumen_por_alimento, catalogo):
        if grupo == SIN_CATALOGAR:
            # BUG-013: un alimento huérfano (ni siquiera está en el catálogo) no es lo mismo que
            # "libre a propósito" -- se marca aparte con st.warning() en vez de un chip normal,
            # para no verse como una categoría más.
            st.warning("⚠️ Sin catalogar -- revisar en Configuración (\"Ingredientes huérfanos\")")
        else:
            st.markdown(chip_html(grupo, GRUPO_ETIQUETA.get(grupo, "Sin grupo / libre")), unsafe_allow_html=True)
        for alimento, equivalentes in items:
            st.markdown(f"- {alimento} — *{equivalentes} equivalente(s)*")


render()
