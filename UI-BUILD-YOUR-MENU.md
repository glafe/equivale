# UI — "Menú del día" (Streamlit)

Especificación de interacción de `app.py`. Confirmado con el usuario: **picker +/- en enteros de
equivalente, nunca slider libre**, y la UI debe mostrar en vivo si falta o sobra algún equivalente.

## Navegación (reorganizada 2026-08-29, a pedido del usuario)

`app.py` usa la forma de diccionario de `st.navigation()` (secciones con encabezado en la barra
lateral) en vez de una lista plana — a pedido explícito del usuario de que el menú se sintiera
"orgánico e intuitivo para usuarios comunes", agrupado por lo que alguien busca, no por cómo está
hecho por dentro:

```
Guía          -> Cómo funciona
Tu día a día  -> Menú del día (default=True), Menú semanal
Tus recetas   -> Recetas, Ingredientes
Cuenta        -> Personas
Ajustes       -> Configuración
```

- **"Menú del día" sigue siendo la página de entrada** (`default=True`) aunque "Guía" aparezca
  primero en la lista — alguien que ya sabe usar la app no debería ver la guía forzada cada vez
  que abre la app, pero sí debe poder encontrarla fácil si la necesita.
- **Los títulos de nav son más cortos que los `st.title()` de cada página** a propósito
  ("Recetas" en el menú vs. "🧑‍🍳 EquiVale Chef — Editor de recetas" como encabezado): el menú se
  lee de un vistazo, la página ya da el contexto completo una vez adentro. Los nombres de archivo
  (`editor_recetas.py`, `editor_ingredientes.py`) no cambiaron, solo el `title=` visible.
- **Sin menciones a "Mongo"/MongoDB en texto que ve el usuario** (a pedido explícito) — los
  docstrings/comentarios de código sí pueden nombrar la base de datos real, eso es documentación
  para quien mantiene el código, no algo que el usuario final llega a leer.

## Flujo principal

1. **Selector de persona**: dropdown arriba de todo con las personas de la colección `personas`,
   cambia el objetivo aplicable.
2. **Selector de tiempo**: al_despertar | desayuno | colación | comida | cena (tabs de Streamlit,
   `st.tabs`, uno por tiempo — así se ve el día completo sin perder contexto).
3. Dentro de cada tab de tiempo:
   a. Mostrar el **presupuesto diario restante** para la persona seleccionada (objetivo diario de
      `objetivos`, ver `schema.md`, menos lo ya guardado en otros tiempos de ese mismo día) como
      una fila de referencia fija arriba — no un objetivo fijo de este tiempo en particular. El
      reparto entre comidas es libre: no importa si la persona come todo en un solo tiempo o en
      seis, solo el total del día (decisión confirmada con el usuario, 2026-08-24).
   b. **Picker de receta** (2026-08-29, corregido a pedido del usuario: antes filtraba de forma
      estricta y un platillo típico de otro tiempo simplemente no aparecía): `st.selectbox` sobre
      TODO el banco filtrado solo por `personas_vistas` incluya la persona seleccionada (con
      opción de "ver todas" — un platillo probado para una persona puede servir de punto de
      partida para la otra; **marcado por default desde 2026-08-29**, a pedido del usuario, en
      vez de arrancar desmarcado como antes) — sin excluir por `tiempo_tipico`, porque nada impide usar un
      platillo típico de otro tiempo si conviene. Orden de las opciones: primero las recetas cuyo
      `tiempo_tipico` incluye este tiempo (alfabético), luego el resto del banco (también
      alfabético) con su primer `tiempo_tipico` como sufijo de texto (ej. "Pan Francés  ·
      Desayuno") para que se note que no es lo típico de este tiempo — `st.selectbox` no soporta
      HTML por opción, así que no hay color ni columna real ahí, solo el sufijo. Al elegir una
      receta que no es típica de este tiempo, la línea de preview del `vector_equivalentes` se
      completa con un chip gris ("Normalmente: {tiempo}", `chip_muted_html()` en `colores.py`)
      justificado a la derecha vía flexbox — ahí sí hay color/alineación real, porque esa línea es
      markdown propio, no una opción del selectbox. Ver nota de sincronización `al_despertar`/
      `desayuno` en `schema.md`, que hace que ambos tiempos casi siempre aparezcan juntos en el
      grupo "coincide".
   c. Botón "Agregar al tiempo" — permite agregar más de una receta al mismo tiempo (los tiempos
      históricos casi siempre tienen 2 platillos).
   c.1. **Cada receta agregada colapsa/expande su detalle** (2026-08-29, a pedido del usuario, para
      que la lista no se vuelva interminable de steppers conforme se agregan más platillos): el
      contenido de ingredientes/steppers vive dentro de un `st.expander(nombre_receta, key=...)`
      -- colapsado se ve solo el nombre (repaso rápido de qué ya se agregó), expandido se pueden
      ajustar porciones. Solo la última receta de la lista (la más reciente) arranca expandida;
      el resto arranca colapsado. El botón "quitar" (ahora un ícono 🗑️) vive FUERA del expander,
      en una columna angosta al lado, para poder quitar una receta sin necesidad de expandirla
      primero.
      - **Corregido el mismo día tras QA en vivo**: `st.expander` no es un widget "de valor" como
        `st.checkbox` -- una vez que su `key` existe, el navegador recuerda el toggle real del
        usuario y `expanded=` deja de tener efecto en reruns futuros, sin importar qué se deje en
        `session_state` (a diferencia de widgets como `st.checkbox`/`st.text_input`, donde SÍ
        alcanza con sobreescribir `session_state` antes de un `st.rerun()` -- mismo patrón que
        `_fecha_pendiente`, que no sirvió aquí). La solución fue darle una key con un "epoch"
        (`st.session_state["_receta_epoch"]`, un contador por `instancia_id` que sube cada vez
        que se agrega otra receta al mismo tiempo) -- así cada vez que hace falta forzar el
        colapso, la key cambia y Streamlit trata el expander como recién creado, respetando
        `expanded=` una vez más.
      - **Reordenar** (2026-08-30, a pedido del usuario, para mejorar la lectura cuando hay
        varias recetas agregadas al mismo tiempo): dos botones angostos "🔼"/"🔽" junto al de
        quitar (fuera del expander, mismo criterio de no tener que expandir para actuar) que
        intercambian la posición de esa tarjeta con la anterior/siguiente en `dia["tiempos"]
        [tiempo]` -- deshabilitados en los extremos (el primero no puede subir, el último no
        puede bajar). No afecta el mecanismo de "epoch" de arriba -- el `instancia_id` de cada
        una no cambia al reordenar, así que el estado de colapso/expansión de cada tarjeta se
        conserva tal cual quedó, solo cambia el orden en que aparecen.
      - **Título del platillo con más peso visual** (2026-08-30, a pedido del usuario): el nombre
        de la receta (título del expander) se ve más grande y en negrita que los ingredientes de
        adentro -- CSS dirigido por `key=` (`nutriguia/estilo.py`, selector `div[class*="st-key-
        exp_receta_"] summary [data-testid="stMarkdownContainer"] p`), para distinguir de un
        vistazo el nombre del platillo de su lista de ingredientes.
   d. Por cada receta agregada, listar sus ingredientes (dentro del expander de arriba). Para cada
      ingrediente **ajustable** (`paso_equivalente()` no da `None`): un control +/- (`st.button("-")`
      / `st.button("+")` a los lados de un número, NO `st.slider`) que sube/baja de 1 en 1
      equivalente. Mostrar junto la cantidad real resultante (ej. "150 g (5 equivalentes)")
      recalculada con `cantidad_por_equivalente` del catálogo -- **el "(N equivalentes)" en el
      color del grupo SMAE de ese ingrediente** (2026-08-30, a pedido del usuario, `chip_html()`
      igual que en el resto de la app) en vez de texto plano, para que un vistazo rápido a la
      cantidad ya diga a qué grupo cuenta. Ingredientes no ajustables (placeholders, items
      compuestos) se muestran fijos, sin stepper.
   d.1. Ingredientes marcados `opcional` (ver `schema.md`) traen además un checkbox **Incluir**,
      marcado por default (reproduce la versión más completa de la receta). Si se desmarca, ese
      ingrediente no cuenta en la suma de equivalentes de ese tiempo — no hace falta "quitarlo" de
      la receta ni que existan dos recetas casi iguales solo por ese extra.
   e. **Panel de estado en vivo**, uno por grupo SMAE presente en el presupuesto diario restante o
      en lo seleccionado en este tiempo: barra o chip con presupuesto restante / actual de este
      tiempo / delta. Color:
      - verde = `estado_por_grupo` da "exacto"
      - amarillo = "falta" (delta > 0)
      - rojo = "excedido" (delta < 0)
      Recalcular en cada interacción (Streamlit lo hace solo al re-ejecutar el script — no
      necesita JS ni websockets).
      - **Cereal/Leguminosa intercambiables** (2026-08-30, a pedido del usuario: "un cereal puede
        ser intercambiable por 1 leguminosa"): antes de calcular el color/ícono, el delta pasa por
        `ajustar_delta_por_intercambios()` (`nutriguia/validation.py`) -- si falta Cereal y sobra
        Leguminosa (o viceversa), el excedente de uno cubre el faltante del otro hasta agotar el
        menor de los dos, así que alguien que comió, por ejemplo, 1 Cereal de menos pero 1
        Leguminosa de más ve ambos grupos en verde ("exacto"), no ambos en amarillo/rojo. Mismo
        criterio aplicado en el resumen del día, al guardar (`estado`/`dia_completo`), al clonar a
        otra persona, y al recalcular un día ya guardado tras un renombrado en el catálogo
        (`BUG-013`). Fijo por ahora (no varía por persona/periodo, a diferencia del campo histórico
        `grupos_intercambiables` de `menus` en `schema.md`) -- nadie lo pidió configurable todavía.
   f. Botón "Guardar tiempo" — SIEMPRE habilitado (el usuario puede querer guardar en progreso),
      pero si no todo está en verde mostrar una advertencia inline ("2 equivalentes de Cereal sin
      cubrir") antes de confirmar, no bloquear silenciosamente.
4. **Resumen del día** (fuera de los tabs, siempre visible — `st.sidebar` o sección fija arriba):
   objetivo diario vs. suma de los tiempos guardados, mismo esquema de color.
5. **Selector de fecha** (`st.date_input`, default hoy) — el plan que se arma es "el plan de la
   persona X para la fecha Y". Botón "Guardar menú del día" hace upsert por `(persona, fecha)` en
   `menus_construidos` (ver `schema.md`) — si ya existe un plan guardado para esa persona+fecha, lo
   sobreescribe (no crea un duplicado). `estado` se infiere solo: `"completo"` si el delta diario
   total es exacto en todos los grupos, si no `"en_progreso"`.
5.1. **Nombre opcional** (2026-08-29, a pedido del usuario, junto a la fecha): un `text_input`
   para darle un nombre al día (ej. "Menú 1"). Ponerle nombre es lo que lo vuelve elegible desde
   "Menú semanal" (ver esa sección abajo) — sin nombre, el día se guarda igual pero solo queda
   como bitácora de esa fecha. El nombre debe ser único por persona entre los días CON nombre
   (`_nombre_en_uso_por_otra_fecha()` valida esto al guardar; si choca, error inline y no se
   guarda — el usuario decide si cambia el nombre o abre el otro día desde el historial).
6. **Historial** (2026-08-27, a pedido del usuario: una persona puede tener varios planes
   guardados, uno por fecha, y poder volver a verlos): sección/expander que lista los
   `menus_construidos` ya guardados de la persona seleccionada, ordenados por `fecha` descendente
   (mostrar fecha + `estado`). Elegir uno de la lista carga ese plan completo de vuelta a
   `st.session_state` (mismo mecanismo de round-trip que abrir cualquier día ya guardado) — no
   hace falta un buscador elaborado, un `st.selectbox`/lista simple basta para el volumen esperado
   (uso personal, no cientos de planes). **Reubicado (2026-08-30, a pedido del usuario)**: vive
   justo debajo del selector de "Persona", no al final de la página -- abrir/editar un día ya
   guardado es de lo que más se usa, así que no debería requerir bajar toda la página cada vez. El
   orden de renderizado no le importa a la lógica de `_fecha_pendiente`/`_nombre_pendiente` (ver
   comentario en `render()`): esos se aplican a `session_state` antes de instanciar los widgets de
   fecha/nombre sin importar dónde en la página viva el botón "Abrir" que los dispara.
6.1. **"🧬 Clonar" a otra persona** (2026-08-30, a pedido del usuario -- cierra `FR-008`): junto a
   "Abrir", en cada fila del historial, un `st.popover` con un selector de persona destino y una
   fecha (default hoy). Al confirmar, `_clonar_a_persona()` copia ese día (recetas + ingredientes
   + ajustes tal como quedaron) directo a Mongo para la persona destino, **sin** cargarlo en el
   editor actual (la persona que se está editando no cambia) -- el flujo es clonar, luego cambiar
   el selector de "Persona" arriba de todo a la destino y abrirlo desde su propio historial para
   ajustar cantidades con los steppers de siempre. `objetivo_diario`/`actual_diario`/`delta_diario`/
   `estado` se recalculan contra el objetivo de la persona destino (no se copian los de origen) --
   los equivalentes clonados casi seguro no cuadran exacto con el nuevo objetivo, y ajustar eso es
   justo la parte que se espera hacer después. Si el `nombre` original ya está en uso por otra
   fecha de la persona destino, se guarda **sin nombre** (para no violar "nombre único por
   persona") y el mensaje de éxito lo avisa explícitamente. Funciona sobre cualquier día del
   historial, tenga nombre o no. **Corregido `BUG-011` (0.21.0)**: si la persona destino ya tiene
   un plan guardado para la fecha elegida, el popover lo avisa con `st.warning()` (nombre del
   plan existente incluido, si tiene) ANTES de mostrar el botón "Clonar" -- antes clonar
   sobreescribía ese plan sin ningún aviso, a diferencia de "Guardar" (donde lo que se
   sobreescribe siempre está a la vista en pantalla).
6.2. **Ingrediente suelto sin receta** (2026-08-30, a pedido del usuario -- cierra `FR-007`): un
   `st.expander("➕ Agregar un ingrediente suelto (sin receta)")` colapsado, debajo del picker de
   recetas de cada tiempo -- para alimentos que conviene comer directo (ej. una fruta) sin crear
   una "receta" de un solo ingrediente en el banco solo para eso. Busca en
   `cargar_nombres_alimentos()` (el catálogo completo, no `cargar_recetas()`) y agrega una
   `RecetaInstancia` sintética de un solo ingrediente con **`receta_id: None`** (ver `schema.md`)
   en vez de un id real -- así se distingue de una receta de verdad sin campo nuevo. Reutiliza el
   mismo stepper +/- y el mismo mecanismo de colapso/epoch que una receta agregada normal; el
   título de su tarjeta se marca "🍏 {alimento} (suelto)" para no confundirse. `grupo_smae` se
   auto-llena desde `catalogo_alimentos.grupo` (puede ser `null` si el alimento es libre, ej. una
   especia -- mismo criterio que cualquier otro ingrediente libre). `_check_recetas_huerfanas()`
   en Configuración ignora `receta_id: None` explícitamente -- no es una referencia rota.
   **Limitación conocida**: como no vive en `recetas`, un ingrediente suelto no aparece en "¿Dónde
   se usa un ingrediente?" de Configuración (esa búsqueda solo mira el banco de recetas) -- no se
   persiguió por ahora, el caso de uso es puntual (un alimento en un día específico), no un patrón
   que se repita entre recetas.

## Página "Personas" (2026-08-27, a pedido del usuario)

Página nueva en la barra lateral (mismo patrón que el Editor de recetas — selector "— Nueva
persona —" / persona existente).

- **Crear**: nombre (persona_id, texto libre — validar que no choque con uno ya existente) +
  objetivo diario: un `number_input` por cada uno de los 7 grupos SMAE canónicos (default 0 = ese
  grupo no aplica para esta persona). Guardar hace `insert` en `personas` y en `objetivos` (con
  `vigente_desde` = hoy, y `equivalentes_diarios` solo con los grupos que quedaron > 0).
- **Editar**: igual formulario pre-cargado con el objetivo vigente de esa persona. Guardar
  sobreescribe el único `objetivos` de esa persona (upsert por `persona` — NO se lleva historial de
  versiones anteriores en esta fase, ver "Ideas para más adelante" en `BUILD-PLAN.md`).
- No hay botón de eliminar persona en esta fase — borrar una persona dejaría huérfanas referencias
  en `menus`/`recetas.personas_vistas`/`menus_construidos`, fuera de alcance por ahora.

## Página "Menú semanal" (2026-08-29, a pedido del usuario; corregida el mismo día)

El usuario en la vida real no arma un día distinto cada vez — alterna entre un ciclo fijo de
menús (ej. "Menú 1" lunes/miércoles/viernes, "Menú 2" martes/jueves/sábado, domingo libre/"cheat
day"). Antes de construir la lista de súper (ver "Ideas para más adelante" en `BUILD-PLAN.md`)
hacía falta poder configurar y **ver de un vistazo** ese ciclo — de ahí esta página.

**Corregida el mismo día tras aclaración del usuario**: la primera versión traía su propio picker
de recetas simplificado (sin steppers ni opcionales), guardado en una colección aparte
(`plantillas_semana`). El usuario aclaró que el flujo real que tenía en mente era otro: primero
armar un día normal y completo en **"Menú del día"** (con todo su detalle — steppers,
ingredientes opcionales, comparación contra el objetivo) y ponerle un **nombre** ahí mismo para
poder reutilizarlo, en vez de mantener un segundo constructor de menús más pobre en paralelo. Se
retiró `plantillas_semana` por completo (ver `schema.md` → sección "removida") y "Menú semanal"
pasó a ser puramente una herramienta de **asignación y consulta**, no de construcción:

- **Cobertura de la semana** (arriba de todo, es la pregunta que motivó la página): 7 columnas
  Lun-Dom, cada una mostrando el nombre del menú asignado o "Libre" (o una advertencia si el
  nombre asignado ya no corresponde a ningún día guardado — ver "Configuración" más abajo).
- **Asignar menús a los días**: un `st.selectbox` por día (Lun-Dom), con opciones = los nombres de
  los días de esa persona guardados con nombre en `menus_construidos` + "Libre/descanso"; un solo
  botón "Guardar asignación" para los 7 a la vez. Esto sigue viviendo en `asignacion_semanal` (ver
  `schema.md`), solo cambió de dónde saca los nombres válidos.
- **"Tus menús" es de solo lectura**: lista cada día guardado con nombre de la persona
  seleccionada (nombre, fecha, chips de equivalentes reales — `actual_diario`, no el objetivo).
  No hay botón para agregar, editar ni borrar recetas desde aquí — un `st.page_link` lleva
  directo a "Menú del día" para eso. Si `actual_diario` no cuadra con el objetivo, se nota en los
  chips igual que en "Menú del día" — esta página no vuelve a validar nada, solo muestra lo que ya
  se guardó ahí.
- **Qué pasa si un menú asignado se borra o se le quita el nombre**: la referencia en
  `asignacion_semanal.dias` queda apuntando a un nombre que ya no existe — se marca con una
  advertencia visual en "Cobertura de la semana", pero no se limpia sola (ver "Configuración",
  `_check_asignacion_rota()`, que la detecta explícitamente; corregirla es volver a abrir el
  expander "Editar asignación de días" y reasignar ese día).
- **"🖨️ Descargar HTML para imprimir"** (2026-08-29, a pedido del usuario -- primera pieza de FR-003
  "exportar imprimible", adelantada antes del resto de la Fase 5 porque el usuario la pidió
  explícitamente como prueba; **rediseñado por completo el 2026-08-30**, ver abajo; **motor
  cambiado de PDF/ReportLab a HTML el mismo 2026-08-30**, ver "Del PDF al HTML" más abajo):
  `st.download_button` justo debajo de "Cobertura de la semana", generado con
  `nutriguia/html_semanal.py`. Pensado para reemplazar el uso que el usuario le daba antes a un
  Excel armado a mano (fuera de git, `menu-Sep.xlsx` y similares) para tener el menú de la semana
  impreso y a la mano.
  - **Rediseño 2026-08-30**: la primera versión (0.12.0) era una cuadrícula de 7 días x 5 tiempos
    con solo el nombre de cada receta -- el usuario aclaró, tras pedirle revisar cómo usaba de
    verdad `menu-Sep.xlsx`, que lo que necesitaba era poder identificar rápido la relación entre
    el EQUIVALENTE y el INGREDIENTE real (cantidad + alimento), organizado **por menú** (no por
    día), con una nota de a qué días de la semana aplica cada uno -- el patrón exacto de ese
    Excel. Ahora, un bloque por cada menú con nombre de la persona (orden alfabético), fluyendo
    uno tras otro **sin salto de página forzado** (afinado el mismo día -- ver más abajo):
    - Encabezado del bloque: nombre del menú + "Aplica: {días}" (o "Sin día asignado en Menú
      semanal todavía" si ese menú aún no se asignó a ningún día -- así el PDF también sirve como
      referencia completa del banco de menús con nombre, no solo de la semana ya armada).
    - Por cada tiempo con recetas, por cada receta: su nombre, y una tabla con **Grupo | Cantidad
      | Alimento en columnas separadas** (afinado el mismo día a pedido del usuario -- antes
      "cantidad — alimento" iba junto en una sola celda de texto), **una fila por ingrediente**
      (antes varios ingredientes del mismo grupo se apilaban con `<br/>` dentro de una sola fila).
      La celda de Grupo (chip de color con el EQ total de ese grupo en esa receta) se fusiona
      verticalmente (`SPAN`) sobre todas las filas de ingredientes de ese grupo, sin repetir el
      chip. Ingredientes `opcional` no incluidos (`incluido: false`) no aparecen, igual que en el
      resto de la app. La cantidad real se calcula con `paso_equivalente()` + `escalar_cantidad()`
      (mismas funciones que "Menú del día") -- si el alimento ya no está en el catálogo, cae a un
      fallback "`N` equiv." en vez de tronar. Un ingrediente `opcional` que sí quedó incluido NO
      lleva la etiqueta "(opcional)" en este HTML (`BUG-014`, 2026-09-04, a pedido del usuario) --
      ese flag describe una variante posible del banco de recetas, pero a esta altura la decisión
      ya se tomó al armar el día, y la etiqueta solo confundía al dietista sobre si contarlo. En
      "Menú del día"/"Recetas" sí se sigue mostrando -- ahí es donde tiene sentido, porque ahí es
      donde se decide.
    - Chips de "Objetivo diario" (una sola vez, arriba de todo) y "Total real de este menú" (al
      final de cada bloque, con `actual_diario` de ese `menus_construidos`) -- **colores
      estandarizados de EquiVale, no una paleta nueva para el PDF**: mismos `GRUPO_COLOR` que se
      ven en toda la app, con `ETIQUETA_CORTA` (en vez de `GRUPO_ETIQUETA`) porque los nombres
      largos ("Aceites s/proteína") no caben en una columna de chip ni en el ancho fijo de la
      columna de grupo de cada receta. Mismo criterio de texto claro/oscuro por contraste
      (`color_texto_legible()`, factorizado de `chip_html()` para compartirlo con el PDF).
    - Nota final (si aplica): qué días quedaron libres/descanso, y qué días tienen una referencia
      rota en `asignacion_semanal` (nombre que ya no existe) -- mismo criterio de "detectar, no
      arreglar solo" que Configuración.
    - Página vertical (carta), no horizontal como la v1 -- ya no hace falta el ancho de 7 columnas
      de día, y el contenido (nombre + tabla de ingredientes por receta) es naturalmente vertical.
    - **Afinado el mismo 2026-08-30, a pedido del usuario, para usar menos papel al imprimir**:
      letra más chica en todo el documento, márgenes reducidos (16mm -> 10mm), y sin salto de
      página forzado entre menús -- fluyen uno tras otro (separados por una línea delgada) y el
      motor de render solo pasa de página cuando de verdad no cabe más contenido, en vez de
      gastar una hoja completa por cada menú corto.
    - **Recetas a dos columnas** (mismo día -- seguía sobrando la mitad derecha de la hoja): las
      recetas de un mismo tiempo se acomodan de dos en dos, lado a lado, cada una a la mitad del
      ancho de página. Si el tiempo tiene un número impar de recetas, la última va sola a ancho
      completo en vez de dejar una columna vacía.
  - **Del PDF (ReportLab) al HTML (2026-08-30, misma tarde, a pedido del usuario)**: tras usar la
    v1 de ReportLab, el usuario prefirió que EquiVale generara el HTML directamente y usar el
    "Imprimir a PDF" del propio navegador -- le da control total de márgenes/escala/qué tanto cabe
    por hoja, algo que ir ajustando a ciegas en ReportLab (ver los tres rediseños de arriba, todos
    el mismo día) no daba. `nutriguia/pdf_semanal.py` se retiró por completo (y `reportlab` salió
    de `requirements.txt`); `nutriguia/html_semanal.py` lo reemplaza con el mismo contenido y
    diseño visual (mismo `GRUPO_COLOR`, mismo agrupamiento por menú/tiempo, mismas dos columnas),
    solo cambia el motor:
    - La celda de Grupo (chip de color con el EQ del grupo en esa receta) usa `rowspan` nativo de
      HTML en vez de `Table` + `SPAN` de ReportLab -- mismo resultado visual, sin calcular rangos
      de fila a mano.
    - Las dos columnas por tiempo son CSS Grid (`grid-template-columns: 1fr 1fr`) en vez del
      emparejado manual de recetas -- la última receta de un tiempo con número impar se marca con
      una clase `receta-completa` (`grid-column: 1 / -1`) para ocupar el ancho completo.
    - `break-inside: avoid` (CSS) en cada tarjeta de receta reemplaza `KeepTogether` de ReportLab
      -- evita que una receta se corte a la mitad justo en un salto de página, tanto al imprimir
      como al exportar a PDF desde el navegador.
    - **Sí trae los emoji de tiempo** (🌅🍳🍎🍽️🌙, iguales a los de la app) -- a diferencia de
      Helvetica en ReportLab, cualquier navegador los renderiza bien.
    - Es un documento HTML autocontenido (CSS embebido, sin fuentes ni scripts externos) --
      `st.download_button` con `mime="text/html"`; el usuario lo abre y usa Ctrl/Cmd+P.
    - `nutriguia/html_semanal.py` sigue sin tocar Mongo -- recibe `asignacion`/`menus_por_nombre`/
      `catalogo` ya resueltos desde `views/menu_semanal.py` (mismo patrón que
      `nutriguia/validation.py`), con `tests/test_html_semanal.py` sobre datos sintéticos.
  - Sigue siendo una primera versión de FR-003/Fase 5, no la definitiva -- ajustar según feedback
    de uso real antes de darla por terminada.

## Página "Lista del súper" (2026-08-30, a pedido del usuario -- cierra `FR-004`)

Página nueva (`views/lista_super.py`, en "Tu día a día" después de "Menú semanal" -- depende de
ella) que suma los ingredientes reales de la semana ya asignada en "Menú semanal" en una lista
consolidada de compras. **Solo lectura**: no arma ni edita nada, igual que "Menú semanal" -- si
falta un día por asignar, se arregla ahí, no aquí.

- **Selector de persona(s)**: `st.multiselect`, no un solo `st.selectbox` como el resto de la app
  -- a pedido explícito del usuario (actualización del mismo 2026-08-30 sobre el `FR-004`
  original) para el caso de dos personas que viven juntas y hacen un solo súper. El mismo alimento
  de ambas se consolida en una sola línea de la lista, no dos separadas.
- **Una ocurrencia por DÍA, no por menú**: si "Menú 1" aplica a lunes/miércoles/viernes en
  `asignacion_semanal`, sus ingredientes se suman 3 veces (`_ingredientes_de_la_semana()`,
  itera los 7 días, no los nombres de menú únicos) -- es la cantidad real que hay que comprar para
  toda la semana, no una porción del menú. Ingredientes `opcional` con `incluido: false` no
  cuentan, igual que en el resto de la app.
- **Consolidación por alimento**: `sumar_por_grupo(ingredientes, "alimento", "equivalentes")` --
  resulta que esa función (pensada originalmente para sumar por `grupo_smae`) ya es lo bastante
  genérica para agrupar por cualquier campo, así que no hizo falta una función nueva
  `sumar_por_alimento()` como sugería el `Eng Description` original del `FR-004` en `BUGS.md`.
- **Agrupado por grupo SMAE para mostrarse** (no una lista plana): el grupo de cada alimento se
  resuelve contra `catalogo_alimentos.grupo` (no contra el `grupo_smae` de ningún ingrediente en
  particular, que ya no se conserva tras sumar por alimento) -- mismo `GRUPO_COLOR`/`GRUPO_ETIQUETA`
  de siempre, orden fijo de grupos (no alfabético), alfabético dentro de cada grupo. Un alimento
  libre a propósito (`grupo: null` en el catálogo, ej. una especia) cae en una sección final "Sin
  grupo / libre" -- no se pierde de la lista, solo no tiene un grupo con el que colorear su
  encabezado. **Corregido `BUG-010` (0.21.0)**: `agrupar_alimentos_por_grupo()`
  (`nutriguia/html_lista_super.py`, pública) es la ÚNICA función que hace este agrupamiento --
  antes la vista previa en pantalla tenía su propia copia de la misma lógica, con el mismo bug
  (un alimento con un `grupo` que no fuera ninguno de los 7 canónicos desaparecía en silencio de
  ambas, en vez de caer en una sección propia al final).
  - **Corregido `BUG-013` (0.24.0)**: un alimento **huérfano** (ni siquiera está en el catálogo --
    típicamente porque se renombró/fusionó ahí pero un día ya guardado se quedó con el nombre
    viejo, ver "Configuración" arriba) ya NO se mezcla con "Sin grupo / libre" -- antes ambos casos
    caían en la misma sección y un huérfano se veía como si de verdad no hiciera falta comprarlo
    (ej. "Leche" huérfana mostrándose como libre en vez de como AOA). Ahora tiene su propia sección
    "⚠️ Sin catalogar" (`SIN_CATALOGAR`, sentinel interno distinto de `None`), con un color de
    alerta (`#6B4C9A`, distinto de los 7 `GRUPO_COLOR` y del gris de "Libre") en el HTML
    descargable, y un `st.warning()` en la vista previa en pantalla en vez de un chip normal.
- **Cantidad real**, no solo el conteo de equivalentes: `cantidad_real()` (factorizado 2026-08-30 a
  `nutriguia/cantidades.py` desde el antiguo `_cantidad_real()` privado de `html_semanal.py`, para
  compartirlo entre ambos) -- mismo fallback "`N` equiv." si el alimento no está en el catálogo.
- **"🖨️ Descargar HTML para imprimir"**: mismo patrón que "Menú semanal" -- `nutriguia/
  html_lista_super.py` genera un documento HTML autocontenido (CSS embebido, misma identidad
  visual "Barro") con un cuadrito `☐` antes de cada alimento para poder tacharlo a mano en el
  súper; el usuario lo abre en su navegador y usa Ctrl/Cmd+P. No toca Mongo -- recibe los datos ya
  resueltos desde la vista, con `tests/test_html_lista_super.py` sobre datos sintéticos.
- **Vista previa en pantalla** (antes del botón de descarga): la misma agrupación por grupo SMAE,
  como chips + lista markdown -- para revisar rápido sin tener que descargar el HTML primero.
- **Referencias rotas**: si un día de `asignacion_semanal` apunta a un nombre que ya no existe en
  `menus_construidos`, se avisa con `st.warning()` (mismo criterio de "detectar, no arreglar solo"
  que Configuración/"Menú semanal") y también se lista en una nota al final del HTML descargado.
- **Fuera de alcance de esta primera versión** (ver `Eng Description` de `FR-004` en `BUGS.md`):
  generar la lista sobre un solo día suelto de `menus_construidos` sin depender de
  `asignacion_semanal` -- el caso de uso principal pedido fue la semana completa; se agrega si
  hace falta tras usarla.
- **Caveat conocido** (`KC-003`): algunos alimentos libres (`grupo_smae: null`, ej. una especia)
  muestran una cantidad de "0" en vez de algo útil para comprar -- viene de que `equivalentes` de
  un ingrediente libre nunca importó antes de esta página (no cuenta para ningún presupuesto), así
  que el banco de recetas no es consistente en qué valor le puso. Se revisa a ojo por ahora, ver
  `BUGS.md` para el detalle y las opciones de arreglo de raíz pendientes de decidir.

## Página "Configuración" (2026-08-29, a pedido del usuario)

El usuario sigue encontrando datos inconsistentes/repetidos a nivel práctico mientras usa la app
(ver regla 9 de `CLAUDE.md`) y pidió una herramienta dedicada a **identificar y corregir
relaciones rotas entre colecciones** — Mongo no las valida solo, son referencias por
nombre/id sueltas, no llaves foráneas (`recetas.ingredientes[].alimento` -> `catalogo_alimentos`,
`*.receta_id` -> `recetas`, `asignacion_semanal.dias.*` -> `menus_construidos.nombre` -- corregido
2026-08-29, era `plantillas_semana` antes de retirar esa colección). Página nueva al
final de la barra lateral (ícono de engrane), pensada como punto de entrada para más herramientas
de administración a futuro, no solo limpieza de datos.

**Factorizado a `nutriguia/chequeos.py` (2026-08-31, a pedido del usuario, misma sesión que agregó
el badge de alertas de abajo)**: la lógica de detección de cada chequeo (antes mezclada con su
renderizado, adentro de `views/configuracion.py`) ahora vive en funciones puras-ish (tocan Mongo,
pero sin nada de Streamlit) en `nutriguia/chequeos.py` -- una función por chequeo, cada una
regresando la lista/dict de "problemas" que antes se armaba inline. `views/configuracion.py` las
llama para renderizar exactamente igual que antes; `app.py` las reutiliza (vía `total_alertas()`)
para el badge, así que el criterio de "qué cuenta como problema" nunca puede desalinearse entre
los dos lugares que lo usan.

**Badge de alertas junto a "Configuración" en la barra lateral (2026-08-31, a pedido del
usuario)**: esa página no se visita seguido, así que sus hallazgos pueden acumularse sin que nadie
se entere a tiempo. `chequeos.total_alertas()` cuenta cuántos CHEQUEOS (no problemas individuales)
tienen algo que revisar -- un número de 0 a 9, más legible en un badge que la suma de problemas
sueltos -- y `app.py` lo agrega al `title` del `st.Page` de Configuración cuando es mayor a cero
(ej. "Configuración 🔴 3"); el ícono ⚙️ se queda igual siempre, para no perder el reconocimiento
visual del ítem de navegación. Cacheado 60s (`@st.cache_data`, invalidado por cada botón de
arreglo con `chequeos.invalidar_cache_alertas()`) porque `app.py` se re-ejecuta completo en CADA
interacción de CUALQUIER página de la app, no solo al navegar a Configuración -- sin cache este
chequeo completo correría de más en cada clic en toda la app. Envuelto en `try/except` a
propósito: un problema pasajero leyendo Mongo para el badge no debe tumbar la navegación de toda
la app, en el peor caso el badge simplemente no aparece esa vez.

- **Buscar relaciones** (lookup manual, dos columnas):
  - "¿Dónde se usa un ingrediente?" (renombrado 2026-08-31, antes "¿En qué recetas...", a pedido
    del usuario tras corregir la cantidad de "Pasta cocida" en el catálogo y querer revisar dónde
    aplicaba) — selectbox de `catalogo_alimentos`, lista **tanto** las recetas del banco que lo
    referencian (con sus equivalentes y si está bloqueado/opcional) **como** los días ya guardados
    de "Menú del día" que lo usan (persona, día, tiempo, y si vino de una receta o como
    ingrediente suelto -- FR-007). Necesita mirar ambas colecciones por la misma razón que
    `BUG-013`: una receta corregida en el banco no actualiza los días que ya se guardaron con su
    versión anterior, y un ingrediente suelto nunca vive en `recetas` para empezar. Sirve para
    confirmar que un ajuste al catálogo (ej. una `cantidad_por_equivalente` corregida) se ve bien
    en todos los lugares donde ese alimento aparece -- aunque, importante: cambiar
    `cantidad_por_equivalente` **no** desincroniza nada por sí solo (`equivalentes` en cada receta/
    día es un conteo entero, independiente del valor en gramos/taza/etc.), así que ningún chequeo
    automático se dispara por esto -- la cantidad real mostrada en toda la app se recalcula sola
    con el valor corregido, sin tocar ningún documento.
  - "¿Dónde se usa una receta?" — selectbox de `recetas`, lista los días guardados de "Menú del
    día" y los menús de "Menú semanal" que la incluyen.
- **Chequeos automáticos** (cada uno independiente, con éxito en verde si no hay problemas):
  - **Ingredientes huérfanos** (renombrado a "🥕 Ingredientes que ya no están en el catálogo",
    2026-08-30 -- ver `BUG-013`): un `ingrediente.alimento`, ya sea de alguna receta del banco O
    de un día ya guardado en `menus_construidos`, que ya no está en `catalogo_alimentos`. Escanea
    ambas colecciones (antes solo miraba `recetas` -- un alimento fusionado/renombrado en el
    catálogo quedaba huérfano PARA SIEMPRE en cualquier día ya guardado que lo usara, aunque el
    banco ya estuviera limpio, y ese caso no aparecía en ningún lado para corregirlo) y muestra por
    separado dónde aparece cada uno ("En recetas: ..." / "En días ya guardados: ..."). Dos opciones
    por alimento (2026-08-29, a pedido del usuario): **Opción A** catalogarlo como alimento nuevo
    (nombre + grupo ya vienen de donde se detectó, solo falta la cantidad por equivalente) —
    arregla todo lo que lo usa a la vez, en ambas colecciones, sin necesitar renombrar nada (una
    vez que existe en el catálogo, deja de ser huérfano en cualquier lado); **Opción B** declarar
    que ya es el mismo que un alimento existente (`_renombrar_en_recetas()` +
    `_renombrar_en_menus_construidos()`, mismo mecanismo que la fusión del Editor de ingredientes)
    — para cuando el ingrediente huérfano es solo una variante de escritura de algo que ya tienes
    catalogado, en vez de crear un duplicado. `_renombrar_en_menus_construidos()`
    (`nutriguia/validation.py` → `renombrar_ingrediente_en_menu_guardado()`) recalcula
    `actual`/`actual_diario`/`delta_diario`/`estado` de cada día tocado -- `objetivo_diario` no se
    toca, sigue siendo el snapshot original de cuando se guardó ese día.
  - **Referencias a recetas eliminadas**: un `receta_id` en `menus_construidos` (corregido
    2026-08-30 -- este chequeo nunca miró `plantillas_semana`, esa colección ya no existe desde
    0.9.0) que ya no existe en `recetas`. Los días guardados de "Menú del día" son bitácora
    histórica y solo se listan, no se editan desde aquí (mismo criterio que `menus` — ver
    `ARCHITECTURE.md` decisión #2); se corrige abriendo ese día desde "Menú del día".
  - **Vector de equivalentes desincronizado**: el `vector_equivalentes` guardado de una receta no
    coincide con la suma real de sus ingredientes — botón "Recalcular y guardar".
  - **Ingredientes duplicados dentro de una misma receta o día guardado** (2026-08-30, ver
    BUG-009 en `BUGS.md`; extendido a días guardados el 2026-08-31): el mismo `alimento` listado
    2+ veces dentro de una receta del banco O de una instancia de un día ya guardado -- a
    diferencia de "posibles duplicados en el catálogo" (abajo), aquí SÍ se fusiona con un clic sin
    pedir confirmación, porque no hay ambigüedad (es el mismo nombre exacto, no dos nombres
    parecidos que podrían ser alimentos distintos). Usa `fusionar_ingredientes_duplicados()` de
    `nutriguia/validation.py` -- suma los `equivalentes` de las filas repetidas en una sola, sin
    cambiar el total por grupo. Este era el bug real detrás de "recetas con el mismo ingrediente
    dos veces" que el usuario encontró limpiando el catálogo a mano: "🔗 Usar este" (arriba) podía
    dejar un duplicado si la receta ya tenía un ingrediente con el nombre destino -- ya corregido
    en `_renombrar_en_recetas()` para que no vuelva a pasar. La variante de días guardados
    (`fusionar_duplicados_en_menu_guardado()`, identifica la instancia por posición dentro de
    `seleccion` -- un día guardado no tiene `instancia_id`) cubre el mismo caso que `BUG-013`:
    corregir la receta en el banco no toca los días que ya se guardaron con el duplicado.
  - **Posibles duplicados en el catálogo**: pares de nombres con similitud alta (`difflib`,
    umbral 0.82 sobre el nombre normalizado — sin regex ni IA) — no fusiona automático, un botón
    "Fusionar" hace `st.switch_page()` al Editor de ingredientes con ese alimento pre-seleccionado
    para que el usuario decida y confirme el renombrado (que ya dispara la fusión si el nombre
    destino coincide con uno existente, ver sección "Editor de ingredientes" arriba). La lista
    muestra la `cantidad_por_equivalente` de cada lado — fusionar solo cambia el nombre en las
    recetas, no reconcilia `equivalentes` ya guardados si las dos medidas eran distintas, así que
    hay que revisar esas recetas después si de verdad importa la diferencia. Un botón aparte
    **"Son diferentes"** guarda el par en `duplicados_descartados` (2026-08-29, a pedido del
    usuario) para que no se vuelva a sugerir — reversible desde un expander "Pares marcados como
    diferentes" en la misma sección.
  - **Personas sin objetivo diario** y **asignación semanal apuntando a un menú eliminado** —
    chequeos más chicos, mismo patrón de aviso + acción corta.
  - **Días guardados con estado desactualizado** (nuevo 2026-08-31, a pedido del usuario -- red de
    seguridad general, no ligado a un bug puntual): `estado`/`delta_diario` de un
    `menus_construidos` se calculan UNA vez, al guardarlo -- si el criterio de qué cuenta como
    "completo" cambia después (ej. Cereal/Leguminosa intercambiables, v0.26.0) y ese día no se
    vuelve a abrir/guardar, se queda mostrando el criterio viejo en el historial de "Menú del
    día". Recalcula `actual_diario`/`delta_diario`/`estado` con la lógica ACTUAL
    (`delta_objetivo()` + `ajustar_delta_por_intercambios()`) y compara contra lo guardado --
    "Recalcular y guardar" solo actualiza esos tres campos, ningún ingrediente.
- **Por qué "detectar y enlazar a la corrección" en vez de arreglar todo automático**: varias de
  estas situaciones (duplicados, ingredientes huérfanos) requieren criterio humano para decidir
  si de verdad son el mismo dato o no — automatizar el diagnóstico ahorra tiempo, automatizar la
  corrección a ciegas arriesga fusionar/borrar cosas que no debían tocarse.

## Página "Guía" (2026-08-29, a pedido del usuario)

Página de ayuda muy corta (`views/guia.py`) para alguien que no conoce la app — el usuario pidió
explícitamente que lo primero fuera "una relación gráfica de cómo se relaciona cada objeto" para
entender cómo se construye un Menú semanal, con enlaces y resaltado.

- **Diagrama** (`<div>` con `st.markdown(..., unsafe_allow_html=True)`, dos llamadas separadas
  para el `<style>` y el HTML — ver nota de `BUG-005` en el docstring del archivo): 5 nodos
  (Personas, Ingredientes, Recetas, Menú semanal, Menú del día) conectados con flechas de texto
  (→/↓) en un `grid-template-areas` de CSS. Cada nodo es un `<a href="/slug_de_la_pagina">` —
  Streamlit fuerza `target="_blank" rel="noopener noreferrer"` en todo `<a>` renderizado vía
  markdown (aunque el href sea relativo/interno) y elimina cualquier `onclick` que se le ponga,
  así que un clic abre la página destino **en una pestaña nueva**, no navega en el mismo lugar —
  no es un bug, es cómo Streamlit sanitiza `<a>` en markdown (ver `BUGS.md` BUG-008, no intentar
  forzarlo distinto con JS, se elimina de todas formas).
  - **Resaltado al pasar el cursor**: CSS puro con el selector `:has()` (ej.
    `.diagrama:has(#n-recetas:hover) #n-semanal { ... }`) — sin JavaScript. Se evitó `<script>`
    a propósito: un `<script>` insertado vía `unsafe_allow_html` generalmente NO se ejecuta,
    porque Streamlit inserta ese HTML con una asignación a `innerHTML`, y los navegadores no
    corren `<script>` insertado así (comportamiento estándar del DOM, no un bug de Streamlit).
    En un navegador sin soporte de `:has()` simplemente no resalta nada — los enlaces y el
    `:hover` individual de cada nodo siguen funcionando igual.
  - **Responsivo**: el diagrama tiene un ancho mínimo fijo (`min-width`) dentro de un contenedor
    con `overflow-x:auto` — en vez de reacomodar las 5 cajas en una sola columna para teléfono
    (que requeriría "linealizar" una rama real del grafo -- Recetas alimenta tanto a Menú
    semanal como a Menú del día -- y forzosamente sugeriría una relación que no es exacta), en
    pantallas angostas se desliza horizontalmente. Coherente con la regla general de la app: el
    body nunca escrolea de lado, el contenedor ancho sí puede.
- **Pasos numerados debajo del diagrama**: una guía corta en Markdown plano para armar el primer
  Menú semanal (Personas → Ingredientes → Recetas → Menú semanal → Menú del día para un día
  suelto → Configuración si algo se ve mal), más una nota corta aclarando la diferencia entre
  "Menú semanal" (el ciclo que se repite) y "Menú del día" (lo que de verdad se guardó para una
  fecha).
- **No es la página de entrada** — `default=True` sigue en "Menú del día" (ver sección
  "Navegación" arriba); la Guía está para consultarse, no para interponerse en el uso diario.
- **Expander "¿Qué grupos cubre 'Agregar de SMAE'?"** (2026-08-29, a pedido del usuario): explica
  qué categorías de la tabla SMAE sí/no aparecen en el buscador de "Ingredientes" → "Agregar de
  SMAE" (ver sección de esa página más arriba), incluida la regla de leche→AOA por proteína.
  Vive aquí (no en un `.md` del repo) porque el caption de esa página enlaza directo a esta
  sección con `st.page_link` en vez de citar un archivo que el usuario final no puede abrir.

## Qué NO hacer

- No usar `st.slider` para ajustar porciones — el usuario pidió explícitamente pasos +/- de
  equivalente entero, no un rango continuo.
- No bloquear el guardado por una validación incompleta — advertir, no impedir (el usuario puede
  estar armando el menú en varias sesiones).
- No recalcular la aritmética de equivalentes dentro de `app.py` — todo pasa por
  `nutriguia/validation.py` (ver `VALIDATION.md`).
- No dejar que el stepper de un ingrediente baje a 0 o negativo — el mínimo es 1 equivalente (si
  el usuario quiere 0, usa "quitar" en vez de bajar el stepper a cero).

## Wireframe en texto (una pestaña de tiempo, ej. "Comida")

```
┌─ Presupuesto restante del día (persona seleccionada) ──┐
│ Verdura 2   Cereal 2   AOA 4   Aceite s/p 1           │
└────────────────────────────────────────────────────────┘

  [ Selecciona una receta ▾ ]  [ + Agregar ]

┌─ Ceviche de atún (v2) ───────────────────────── [quitar] ┐
│  Atún en agua       1 lata           AOA  3   (fijo)     │
│  Queso panela   [-]  40 g (1)  [+]   AOA  1               │
│  Galleta Salma  [-]  3 pz (1)  [+]   Cereal 1              │
│  Pico de gallo  [-]  1/2 tza(1)[+]   Verdura 1              │
└────────────────────────────────────────────────────────────┘

┌─ Estado del tiempo ──────────────────────────────────┐
│ Verdura   objetivo 2  actual 1   🟡 falta 1            │
│ Cereal    objetivo 2  actual 1   🟡 falta 1            │
│ AOA       objetivo 4  actual 4   🟢 exacto              │
│ Aceite s/p objetivo 1 actual 0   🟡 falta 1              │
└────────────────────────────────────────────────────────┘

  [ Guardar tiempo (incompleto) ]
```

## Convención de colores por grupo SMAE (confirmada con el usuario, 2026-08-24)

La app usa un color fijo por grupo (identidad del grupo, no estado) en cualquier lugar donde se
muestren equivalentes por grupo — panel de estado, resumen del día, editor de recetas. Aproximado
de una referencia visual del usuario; ajustar si no calzan exactamente:

| Grupo canónico | Color   | Etiqueta mostrada       |
|-----------------|---------|--------------------------|
| Fruta           | `#FFC000` | Fruta                  |
| Verdura         | `#00A651` | Verdura                |
| Cereal          | `#F07C22` | Cereal                 |
| Leguminosa      | `#FF0000` | Leguminosas            |
| AOA             | `#A6081C` | AOA (Alimento de origen animal) |
| Aceite s/p      | `#3D4A1E` | Aceites s/proteína     |
| Aceite c/p      | `#6D6E71` | Aceite c/proteína      |

Pastilla (`border-radius: 999px`) con texto oscuro o claro elegido automáticamente según la
luminancia del color de fondo (`luminancia_relativa()`/`color_texto_legible()` en `colores.py`,
compartidas con el PDF de "Menú semanal" -- ver más abajo) — así un color claro como Fruta no
queda con texto blanco ilegible sin tener que listar excepciones a mano. Esto es la
identidad visual del GRUPO — es independiente del color de ESTADO (✅/🔺/🔻ícono de
exacto/falta/excedido); el estado se muestra aparte, no reemplazando el color del grupo. Vive en
`nutriguia/colores.py` como single source of truth para no repetir hex en cada página.

## Identidad visual "Barro" y responsividad (2026-08-27, a pedido del usuario)

El usuario pidió mejorar el diseño general (referencia: sitio `getdesign.md`, estilo "Clay") y
que la app fuera usable desde el teléfono, no solo escritorio. Antes de tocar código se propuso
una maqueta HTML interactiva (artefacto, fuera del repo) con una traducción del estilo "Clay" al
tema real de la app — superficies de barro sin cocer, tarjetas de receta como fichas, los chips
de grupo SMAE como fichas de conteo — y el usuario la aprobó. Resumen de lo implementado:

- **Paleta y tipografía**: fondo/superficie/tinta/acento en `.streamlit/config.toml` (colores
  base, aplicados nativamente por Streamlit a botones/inputs/sidebar) + Google Fonts (Fraunces
  para títulos, Figtree para interfaz, Space Mono para fechas/cantidades) y radios/sombras
  inyectados como CSS desde `nutriguia/estilo.py`, cargado una sola vez en `app.py` antes de
  `pagina.run()` (se aplica a todas las páginas porque `app.py` se re-ejecuta completo en cada
  navegación). Los 7 colores de grupo SMAE de la tabla de arriba **no cambiaron** — son
  funcionales, no decorativos.
- **Acento nuevo** (`#3C6E68`, un verde-azulado tipo esmalte de cerámica): elegido a propósito
  para no parecerse a ninguno de los 7 colores de grupo, así un botón primario no se confunde con
  un chip de grupo.
- **Convención de `key=` para CSS dirigido** (ver comentario en `nutriguia/estilo.py`): Streamlit
  agrega una clase `st-key-<key>` a cualquier widget/contenedor con `key=` explícito — más
  estable que apuntar a las clases `st-emotion-cache-*` (hashes que cambian entre builds de
  Streamlit). Prefijos ya usados y a los que el CSS apunta: `menos_`/`mas_` (botones -/+ de un
  stepper), `receta_card_` (contenedor de una receta agregada), `status_` (panel de estado por
  tiempo o del día). Si agregas un nuevo stepper o tarjeta, sigue el mismo prefijo o el CSS no lo
  alcanzará.
- **Responsividad**: Streamlit apila automáticamente cualquier `st.columns(...)` en pantallas
  angostas (por debajo de ~640px) — no se intentó pelear contra eso con CSS de media queries
  (frágil, depende de internals de Streamlit). En vez de eso, las filas con muchas columnas se
  reestructuraron en 2 filas más cortas y agrupadas lógicamente: en "Menú del día", cada
  ingrediente ahora es "etiqueta" (fila 1) + "stepper -/cantidad/+" (fila 2) en vez de un solo
  renglón de 4-5 columnas; en el Editor de recetas, "alimento + quitar" (fila 1) + "grupo/
  cantidad/equivalentes/bloqueado/opcional" (fila 2) en vez de 7 columnas en una sola fila. En
  escritorio se ve igual que antes (columnas en línea); en móvil, cada fila corta se apila en
  pocos bloques en vez de muchos, y los botones +/- (estilizados como cuadrados táctiles vía
  `st-key-menos_`/`st-key-mas_`) se ven intencionales apilados a ancho completo.
- **Vista oscura (2026-08-30, a pedido del usuario, para leer de noche)**: lo de arriba ("no se
  intentó un tema oscuro nativo") quedó obsoleto -- resultó ser más simple de lo que parecía.
  Streamlit 1.62 SÍ soporta un tema claro y uno oscuro a la vez (confirmado leyendo el código
  fuente instalado en el servidor, `streamlit/config.py` -> `CustomThemeCategories.LIGHT`/`DARK`,
  no documentado de forma obvia): `.streamlit/config.toml` ahora tiene `[theme.light]` y
  `[theme.dark]` (además de `[theme]`, que sigue trayendo solo lo compartido -- `primaryColor`
  claro y `base`). Con eso, Streamlit agrega solo un selector **System / Light / Dark** en el menú
  ⋮ (sin código nuevo) que reteñe TODOS sus componentes nativos (fondo, tarjetas, inputs,
  sidebar) -- "System" sigue la preferencia del sistema operativo/navegador automáticamente.
  - Paleta oscura: mismo espíritu "Barro" (tierra/tinta) invertido, no el gris azulado genérico de
    Streamlit -- `backgroundColor="#1E1A16"`, `secondaryBackgroundColor="#2A2420"`,
    `textColor="#F1ECE3"`, `primaryColor="#6FB0A5"` (el acento `#3C6E68` aclarado para seguir
    siendo legible sobre fondo oscuro).
  - **Lo que Streamlit NO reteñe solo**: el HTML/CSS propio de la app inyectado con
    `unsafe_allow_html` -- el diagrama de "Guía" (`views/guia.py`) ya escribía
    `var(--surface, #F7F4EE)` etc. desde que se creó (2026-08-29), anticipando esto, pero esas
    variables nunca se definían -- siempre caían al valor de respaldo claro, así que el diagrama
    se veía como un rectángulo claro fijo encima del fondo oscuro. Corregido definiendo esas
    variables (`--surface`, `--surface-2`, `--border`, `--ink`, `--ink-faint`, `--accent`) en
    `nutriguia/estilo.py` bajo `@media (prefers-color-scheme: dark)`, con el mismo mecanismo
    cubriendo también los acentos de borde/sombra (`--barro-border`/`--barro-shadow`) que ya
    usaban las tarjetas de "Menú del día".
  - **Por qué `@media (prefers-color-scheme: dark)` y no algo ligado al selector de Streamlit
    directamente**: Streamlit no expone su tema activo como variable CSS reutilizable en ningún
    lado (confirmado inspeccionando la app en vivo -- ni `:root` ni `.stApp` traen
    `--primary-color`/`--background-color`/etc., cada componente nativo recibe su color por JS/
    emotion de forma interna) y las páginas de esta app no corren JavaScript propio (ver nota de
    `BUG-005` sobre por qué el diagrama de Guía usa solo CSS) -- así que la preferencia del
    sistema operativo es la única señal a la que este CSS propio puede reaccionar.
  - **Limitación conocida (`KC-004`, ver `BUGS.md`)**: si alguien elige "Dark" a mano en el menú
    de Streamlit mientras su sistema operativo sigue en modo claro, `prefers-color-scheme` no se
    entera (es una preferencia del SO, no de la página) -- Streamlit sí se pone oscuro, pero el
    diagrama de Guía y los acentos de borde/sombra se quedan en su versión clara hasta que el
    sistema operativo también cambie. Caso raro en la práctica (la mayoría deja "System" y su SO
    cambia solo de noche); no tiene arreglo limpio mientras Streamlit no exponga su tema activo.

## Editor de recetas ("EquiVale Chef") — promovido desde "Ideas para más adelante"

El usuario pidió adelantar esta herramienta (ver nota original en `BUILD-PLAN.md`) porque al usar
"Menú del día" encontró recetas del banco duplicadas o con ingredientes que deberían poder
corregirse. Alcance actual (más acotado que la idea original — sin integración a
`SMAE_CONSULTA.csv` todavía, eso sigue en "Ideas para más adelante"):

- **Navegación**: la app pasa a ser multipágina con `st.navigation`/`st.Page` — barra lateral
  izquierda con "Menú del día" y "Editor de recetas".
- **Listado**: seleccionar una receta existente (buscador por nombre) para editarla, o crear una
  nueva desde cero.
- **Campos editables de la receta**: `nombre`, `tiempo_tipico` (multi-select), `personas_vistas`
  (multi-select).
- **Ingredientes**: agregar fila nueva, quitar fila existente. Por fila: `alimento` (elegir de
  `catalogo_alimentos` o escribir uno libre/nuevo), `grupo_smae` (de los 7 canónicos, o "ninguno"
  para libre), `cantidad`, `equivalentes` (entero), y un checkbox **bloquear edición** que fija
  `Ingrediente.bloqueado` (ver `schema.md`) — evita que ese ingrediente sea ajustable con el
  stepper en "Menú del día" aunque el catálogo sí resuelva un paso.
  - **Al elegir/cambiar el alimento de una fila** (2026-08-25, para evitar inconsistencias tipo
    "Pollo, 200 g, 5 equivalentes" arrastradas de un alimento anterior en la misma fila): si el
    alimento está en `catalogo_alimentos`, se sobreescribe `grupo_smae` (según el catálogo) y se
    resetea `equivalentes` a 1. Esto SOLO pasa en el momento de elegir/cambiar el alimento de esa
    fila, no en cada rerun. No aplica a alimentos libres/nuevos (`(otro / alimento nuevo)`) ni si
    el alimento no está en el catálogo.
  - **`cantidad` es de solo lectura cuando el alimento está en el catálogo** (2026-08-25): se
    calcula sola como `equivalentes × cantidad_por_equivalente` (ej. Pollo a 3 equivalentes ->
    "90 g") usando `nutriguia/cantidades.py` (`escalar_cantidad`, compartido con "Build your
    menu") — nunca editable a mano en ese caso, para que no se pueda desincronizar de
    `equivalentes`. Solo para alimentos libres/nuevos (no resueltos por `paso_equivalente()`,
    ver `VALIDATION.md`) `cantidad` sigue siendo texto libre editable.
- **Resumen en vivo**: `vector_equivalentes` recalculado de los ingredientes actuales (nunca
  editado a mano), mostrado con los chips de color de la tabla de arriba.
- **Guardar**: upsert a `recetas` por `receta_id` (slug generado del nombre, con sufijo `-v2`, etc.
  si ya existe uno con ese nombre pero ingredientes distintos — mismo criterio que el banco
  original, ver `schema.md` → `recetas`). Editar una receta existente conserva su `veces_visto` y
  `origen` (trazabilidad histórica) — el editor no los toca. Una receta nueva creada desde cero
  arranca con `veces_visto: 0`, `origen: []`.
- **Eliminar**: requiere un checkbox de confirmación explícito antes de habilitar el botón —
  eliminar una receta usada en el banco es una acción difícil de revertir.

## Editor de ingredientes (2026-08-27, a pedido del usuario) — cierra FR-002

El usuario necesitaba limpiar el catálogo de alimentos (79 entradas, algunas mal escritas o
duplicadas) antes de seguir agregando más, y tener acceso a la tabla oficial SMAE para agregar
alimentos nuevos sin escribirlos a mano. Esto es la parte de "EquiVale Chef" que faltaba
(`SMAE_CONSULTA.csv`, ver FR-002 en `BUGS.md` — ahora Shipped). Nueva página en la barra lateral,
`views/editor_ingredientes.py`:

- **Tabla** (`st.dataframe`, de solo lectura): todo `catalogo_alimentos`, filtrable por texto y
  por grupo (incluye "(libre, sin grupo)"). Columnas: Alimento, Grupo, Cantidad por equivalente,
  Asunción, **Usado en recetas** (cuántas recetas distintas lo referencian — contexto antes de
  tocarlo, no una restricción). La búsqueda (acá y en "Agregar de SMAE") es insensible a acentos
  vía `nutriguia/texto.py::normalizar_busqueda()` — escribir "atun" sí encuentra "Atún".
- **Editar/eliminar**: un `st.selectbox` (mismo patrón que el editor de recetas y "Personas", NO
  `st.form` — ver nota abajo) para elegir un alimento y mostrar sus campos (nombre, grupo,
  cantidad) en widgets sueltos con botones "Guardar cambios" y "Eliminar" (este último detrás de
  un checkbox de confirmación, mismo patrón que eliminar una receta).
  - **Renombrar hace cascada a `recetas`**: las recetas referencian un alimento por *nombre*, no
    por id (ver `schema.md`) — si el editor solo cambiara el catálogo, cualquier receta que ya
    usara ese alimento quedaría apuntando a un nombre inexistente y ese ingrediente se volvería
    silenciosamente "no ajustable". `_renombrar_en_recetas()` actualiza `ingredientes[].alimento`
    en todas las recetas afectadas y lo reporta ("se renombró en N receta(s)").
  - **Si el nuevo nombre ya existe en el catálogo, se trata como fusión de duplicados** (mismo
    criterio que la regla 9 de `CLAUDE.md`): se borra el registro viejo, se conserva el que ya
    existía tal cual, y las recetas se re-apuntan al nombre que sobrevive. Pensado explícitamente
    para casos como el KC-001 de `BUGS.md` ("Aceite de oliva" vs "Aceite oliva").
  - **Eliminar** por default no toca las recetas que lo usaban (mismo efecto que un alimento
    nunca catalogado: el ingrediente sigue en la receta, pero deja de ser ajustable con el
    stepper). El conteo de "usado en N recetas" se muestra en el mensaje de confirmación para que
    la decisión sea informada, no un bloqueo duro.
  - **Checkbox opt-in "También quitarlo de las N receta(s) que lo usan"** (2026-08-27): si se
    marca, `_quitar_de_recetas()` borra ese ingrediente de `ingredientes[]` en cada receta
    afectada y recalcula su `vector_equivalentes` — para cuando el alimento de verdad no debería
    seguir en esas recetas (ej. se catalogó por error), no solo para el caso de "se volvió no
    ajustable pero sigue siendo parte del platillo". Sin marcarlo, el comportamiento es el de
    siempre (arriba). No confundir con `BUGS.md` KC-001 (ingrediente con ortografía duplicada
    *dentro* de una misma receta) — ese caso sigue sin una herramienta dedicada, se corrige a mano
    desde el Editor de recetas.
  - **`menus` (histórico) nunca se toca** — ni por renombrar ni por fusionar. Es de solo lectura
    por diseño (ver `ARCHITECTURE.md` decisión #2); esta herramienta no reescribe el pasado.
- **"Agregar de SMAE"**: expander con buscador de texto libre sobre `SMAE_CONSULTA.csv` (ahora
  commiteado al repo — es la tabla oficial pública, sin datos de personas, ver nota de privacidad
  en `CLAUDE.md`). Cada fila del CSV ya es una combinación específica de alimento + preparación +
  cantidad + unidad (ej. "Champiñon cocido entero" vs "crudo rebanado" son filas distintas), así
  que mostrar cada fila como una opción del buscador resuelve directamente "elegir una unidad de
  medición" sin necesitar un segundo paso. Alimentos ya existentes en el catálogo se bloquean con
  un aviso ("edítalo arriba") en vez de crear un duplicado.
  - **Categorías SMAE sin equivalente entre los 7 grupos canónicos** (Azúcares, "Leche con
    azúcar" -- helados/malteadas/leches saborizadas --, Bebidas alcohólicas) **no aparecen** en
    el buscador — no hay dónde clasificarlas sin antes decidir si se extienden los 7 grupos, y esa
    es una decisión aparte, no algo para improvisar en este editor.
  - **Leche simple (descremada/semidescremada/entera) sí se soporta, catalogada como AOA**
    (2026-08-29, a pedido del usuario) — pero solo la fila cuya porción sugerida aporta al menos
    `UMBRAL_PROTEINA_LECHE_AOA` (7 g) de proteína; por debajo de eso la fila se excluye igual que
    una categoría no soportada (ej. un yogur bajo en grasa en porción chica no cuenta como
    equivalente de AOA). El caption de este expander enlaza a "Cómo funciona" (`views/guia.py`,
    sección "¿Qué grupos cubre 'Agregar de SMAE'?") en vez de citar este archivo — así el usuario
    ve la explicación sin salir de la app. Ver `nutriguia/smae_csv.py` para la clasificación
    exacta.
  - **Corregido `BUG-012` (2026-08-30)**: el CSV mezcla más de una codificación de caracteres
    entre secciones (parte viene en Latin-1, el resto en UTF-8) — se decodifica todo el archivo
    como Latin-1 (necesario porque nunca falla, a diferencia de intentar UTF-8 con un archivo
    mixto), lo que dejaba las filas en UTF-8 con "mojibake" (ej. "Café" salía como "CafÃ©") — y
    esto además rompía la búsqueda: "CafÃ©" normalizaba a "cafa", no "cafe", así que buscar "café"
    no encontraba "Café en polvo" (el usuario lo reportó). `_reparar_mojibake()` (nuevo en
    `nutriguia/smae_csv.py`) revierte el daño cuando puede: re-codifica el string a bytes Latin-1
    (nunca falla) e intenta decodificarlos como UTF-8 -- si funciona, eran bytes UTF-8 mal leídos
    y usa el resultado corregido; si truena, el texto sí era Latin-1 genuino y lo deja tal cual.
    Se aplica a `alimento`, `unidad` (dentro de `cantidad_por_equivalente`) y `tipo_original`
    antes de devolver cada fila -- la clasificación por categoría (`grupo_smae`) no necesitó
    tocarse, ya era inmune a esto porque solo compara el PREFIJO de `Tipo Equivalente`, que
    siempre es ASCII puro.
- **Por qué widgets sueltos y no `st.form`**: un checkbox "Confirmo eliminar" adentro de un
  `st.form` no puede des-habilitar su propio botón de submit en la misma interacción — los forms
  de Streamlit solo reenvían sus valores al hacer submit, así que el botón quedaría deshabilitado
  sin forma de que el usuario lo vuelva a habilitar con un clic. Mismo patrón ya usado (sin
  `st.form`) en el editor de recetas para su botón de eliminar.

## Notas de implementación Streamlit

- Guardar el estado del menú en construcción en `st.session_state` (por persona+tiempo), no en
  Mongo hasta que el usuario presione "Guardar" — evita escribir en cada click.
- `st.rerun()` no es necesario para los steppers — Streamlit re-ejecuta el script completo en cada
  interacción de widget por diseño; usar `st.session_state` para que los valores no se reseteen.
- Para los +/- de cada ingrediente, usar una key única por ingrediente (`f"{receta_instancia_id}_{alimento}"`)
  para que Streamlit no confunda steppers de dos recetas distintas agregadas al mismo tiempo.
