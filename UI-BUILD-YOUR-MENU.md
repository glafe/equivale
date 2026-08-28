# UI — "Build your menu" (Streamlit)

Especificación de interacción de `app.py`. Confirmado con el usuario: **picker +/- en enteros de
equivalente, nunca slider libre**, y la UI debe mostrar en vivo si falta o sobra algún equivalente.

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
   b. **Picker de receta**: `st.selectbox` filtrado por `tiempo_tipico` que incluya este tiempo Y
      (`personas_vistas` incluya la persona seleccionada, con opción de "ver todas" — un platillo
      probado para una persona puede servir de punto de partida para la otra). Mostrar nombre + su
      `vector_equivalentes` como preview antes de agregar.
   c. Botón "Agregar al tiempo" — permite agregar más de una receta al mismo tiempo (los tiempos
      históricos casi siempre tienen 2 platillos).
   d. Por cada receta agregada, listar sus ingredientes. Para cada ingrediente **ajustable**
      (`paso_equivalente()` no da `None`): un control +/- (`st.button("-")` / `st.button("+")` a
      los lados de un número, NO `st.slider`) que sube/baja de 1 en 1 equivalente. Mostrar junto
      la cantidad real resultante (ej. "150 g (5 equivalentes)") recalculada con
      `cantidad_por_equivalente` del catálogo. Ingredientes no ajustables (placeholders, items
      compuestos) se muestran fijos con un botón "quitar".
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
6. **Historial** (2026-08-27, a pedido del usuario: una persona puede tener varios planes
   guardados, uno por fecha, y poder volver a verlos): sección/expander que lista los
   `menus_construidos` ya guardados de la persona seleccionada, ordenados por `fecha` descendente
   (mostrar fecha + `estado`). Elegir uno de la lista carga ese plan completo de vuelta a
   `st.session_state` (mismo mecanismo de round-trip que abrir cualquier día ya guardado) — no
   hace falta un buscador elaborado, un `st.selectbox`/lista simple basta para el volumen esperado
   (uso personal, no cientos de planes).

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
luminancia del color de fondo (`_luminancia_relativa()` en `colores.py`) — así un color claro
como Fruta no queda con texto blanco ilegible sin tener que listar excepciones a mano. Esto es la
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
  reestructuraron en 2 filas más cortas y agrupadas lógicamente: en "Build your menu", cada
  ingrediente ahora es "etiqueta" (fila 1) + "stepper -/cantidad/+" (fila 2) en vez de un solo
  renglón de 4-5 columnas; en el Editor de recetas, "alimento + quitar" (fila 1) + "grupo/
  cantidad/equivalentes/bloqueado/opcional" (fila 2) en vez de 7 columnas en una sola fila. En
  escritorio se ve igual que antes (columnas en línea); en móvil, cada fila corta se apila en
  pocos bloques en vez de muchos, y los botones +/- (estilizados como cuadrados táctiles vía
  `st-key-menos_`/`st-key-mas_`) se ven intencionales apilados a ancho completo.
- **No se intentó**: un tema oscuro nativo (Streamlit permite un solo tema "custom" a la vez vía
  `config.toml`; el usuario puede seguir alternando Light/Dark/Custom desde el menú de Streamlit,
  pero Dark no tiene la paleta Barro aplicada) — retomar solo si hace falta.

## Editor de recetas ("EquiVale Chef") — promovido desde "Ideas para más adelante"

El usuario pidió adelantar esta herramienta (ver nota original en `BUILD-PLAN.md`) porque al usar
"Build your menu" encontró recetas del banco duplicadas o con ingredientes que deberían poder
corregirse. Alcance actual (más acotado que la idea original — sin integración a
`SMAE_CONSULTA.csv` todavía, eso sigue en "Ideas para más adelante"):

- **Navegación**: la app pasa a ser multipágina con `st.navigation`/`st.Page` — barra lateral
  izquierda con "Build your menu" y "Editor de recetas".
- **Listado**: seleccionar una receta existente (buscador por nombre) para editarla, o crear una
  nueva desde cero.
- **Campos editables de la receta**: `nombre`, `tiempo_tipico` (multi-select), `personas_vistas`
  (multi-select).
- **Ingredientes**: agregar fila nueva, quitar fila existente. Por fila: `alimento` (elegir de
  `catalogo_alimentos` o escribir uno libre/nuevo), `grupo_smae` (de los 7 canónicos, o "ninguno"
  para libre), `cantidad`, `equivalentes` (entero), y un checkbox **bloquear edición** que fija
  `Ingrediente.bloqueado` (ver `schema.md`) — evita que ese ingrediente sea ajustable con el
  stepper en "Build your menu" aunque el catálogo sí resuelva un paso.
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
  - **Eliminar** no toca las recetas que lo usaban (mismo efecto que un alimento nunca
    catalogado: el ingrediente sigue en la receta, pero deja de ser ajustable con el stepper). El
    conteo de "usado en N recetas" se muestra en el mensaje de confirmación para que la decisión
    sea informada, no un bloqueo duro.
  - **`menus` (histórico) nunca se toca** — ni por renombrar ni por fusionar. Es de solo lectura
    por diseño (ver `ARCHITECTURE.md` decisión #2); esta herramienta no reescribe el pasado.
- **"Agregar de SMAE"**: expander con buscador de texto libre sobre `SMAE_CONSULTA.csv` (ahora
  commiteado al repo — es la tabla oficial pública, sin datos de personas, ver nota de privacidad
  en `CLAUDE.md`). Cada fila del CSV ya es una combinación específica de alimento + preparación +
  cantidad + unidad (ej. "Champiñon cocido entero" vs "crudo rebanado" son filas distintas), así
  que mostrar cada fila como una opción del buscador resuelve directamente "elegir una unidad de
  medición" sin necesitar un segundo paso. Alimentos ya existentes en el catálogo se bloquean con
  un aviso ("edítalo arriba") en vez de crear un duplicado.
  - **Categorías SMAE sin equivalente entre los 7 grupos canónicos** (Azúcares, Leche, Bebidas
    alcohólicas) **no aparecen** en el buscador — no hay dónde clasificarlas sin antes decidir si
    se extienden los 7 grupos, y esa es una decisión aparte, no algo para improvisar en este
    editor. Ver `nutriguia/smae_csv.py` para la clasificación exacta.
  - El CSV mezcla más de una codificación de caracteres entre secciones (parte viene en Latin-1,
    el resto no) — se decodifica como Latin-1 (correcto para la gran mayoría de los ~2000 nombres
    soportados) y un puñado puede salir con acentos mal formados; no se persiguió exhaustivamente,
    mismo criterio que la regla 9 de `CLAUDE.md` para nombres de ingrediente parecidos.
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
