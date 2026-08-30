# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto usa
[Versionado Semántico](https://semver.org/lang/es/) (`MAJOR.MINOR.PATCH`). Mientras estemos en
`0.x.x` los cambios que rompen compatibilidad se documentan igual pero no requieren un salto a
`1.0.0` — ese salto está reservado para cuando la Fase 5 (pulido, ver `BUILD-PLAN.md`) esté hecha
y el flujo se haya usado en la vida real sin sorpresas.

Convención de commits desde esta entrada en adelante: `feat:`, `fix:`, `docs:`, `refactor:`,
`test:`, `chore:` como prefijo del mensaje. Los commits previos a esta convención (ver `git log`)
no se reescriben.

Ver también `BUGS.md` para el detalle de bugs/caveats/features (este archivo solo referencia el ID
y un resumen de una línea).

## [Unreleased]

### Added
- (nada pendiente por ahora — próximo trabajo entra aquí)

## [0.19.0] - 2026-08-30

### Added
- **FR-007**: "Menú del día" ahora permite agregar un ingrediente suelto (ej. una fruta) directo a
  un tiempo, sin pasar por una receta del banco -- `st.expander("➕ Agregar un ingrediente suelto
  (sin receta)")` colapsado debajo del picker de recetas, busca en `cargar_nombres_alimentos()`.
  `_nueva_instancia_suelta()` crea una `RecetaInstancia` sintética de un solo ingrediente con
  `receta_id: None` (ver `schema.md`), reutilizando el mismo stepper/colapso que una receta
  normal. `_check_recetas_huerfanas()` en Configuración se ajustó para ignorar `receta_id: None`
  explícitamente -- no es una referencia rota.
- **FR-008**: botón "🧬 Clonar" (en un `st.popover`) junto a "Abrir" en el historial de "Menú del
  día", con selector de persona destino y fecha -- copia ese día completo (recetas, ingredientes,
  ajustes) directo a Mongo para la persona destino, sin cargarlo en el editor actual.
  `_clonar_a_persona()` recalcula `objetivo_diario`/`actual_diario`/`delta_diario`/`estado` contra
  el objetivo de la persona destino (no copia los del origen). Si el `nombre` original ya está en
  uso por otra fecha de destino, se guarda sin nombre para no violar "nombre único por persona" y
  se avisa en el mensaje de éxito.

## [0.18.0] - 2026-08-30

### Changed
- **"Menú semanal" exporta HTML en vez de PDF** -- a pedido del usuario, que prefiere que EquiVale
  genere el HTML y usar el "Imprimir a PDF" de su propio navegador (Ctrl/Cmd+P), con control total
  de márgenes/escala/qué tanto cabe por hoja, en vez de un PDF armado a ciegas con ReportLab.
  `nutriguia/pdf_semanal.py` se retiró por completo (y `reportlab` salió de `requirements.txt`);
  `nutriguia/html_semanal.py` (nuevo) lo reemplaza con el mismo contenido y diseño visual (mismo
  `GRUPO_COLOR`, mismo agrupamiento por menú/tiempo, mismas dos columnas por tiempo):
  - Chip de grupo (con el EQ del grupo en esa receta) fusionado sobre sus filas de ingredientes
    con `rowspan` nativo de HTML, en vez de `Table` + `SPAN` de ReportLab.
  - Dos columnas por tiempo con CSS Grid (`grid-template-columns: 1fr 1fr`) en vez del emparejado
    manual de recetas de dos en dos -- con un número impar, la última se marca `receta-completa`
    (`grid-column: 1 / -1`) para ocupar el ancho completo.
  - `break-inside: avoid` reemplaza `KeepTogether` -- evita que una receta se corte a la mitad en
    un salto de página, tanto al imprimir como al exportar a PDF desde el navegador.
  - Sí trae los emoji de tiempo (🌅🍳🍎🍽️🌙) -- a diferencia de Helvetica en ReportLab, cualquier
    navegador los renderiza bien.
  - `st.download_button` ahora entrega `mime="text/html"` (antes `application/pdf`), botón
    renombrado a "🖨️ Descargar HTML para imprimir".
  - `tests/test_pdf_semanal.py` se retiró; `tests/test_html_semanal.py` (nuevo) cubre los mismos
    casos (semana mixta/libre, sin objetivo, menú sin día asignado, fallback de cantidad sin
    catálogo, ingrediente libre sin "None", dos/tres recetas por tiempo) más uno nuevo de
    escapado de HTML en nombres.
  - Ver `UI-BUILD-YOUR-MENU.md` → "Del PDF al HTML" y `BUGS.md` FR-003 para el detalle completo.

## [0.17.0] - 2026-08-30

### Fixed
- **BUG-009**: "🔗 Usar este" (reemplazar un ingrediente huérfano por uno existente, en
  Configuración/Editor de ingredientes) podía dejar dos filas con el mismo `alimento` en una
  receta en vez de fusionarlas, si la receta ya tenía un ingrediente con ese nombre. Encontrado
  por el usuario limpiando el catálogo a mano (4 recetas afectadas en producción). Nueva función
  pura `fusionar_ingredientes_duplicados()` en `nutriguia/validation.py` (ver `VALIDATION.md`):
  suma los `equivalentes` de las filas repetidas en una sola -- no cambia el total por grupo, así
  que es seguro sin revisar caso por caso. `_renombrar_en_recetas()` (en ambos archivos) ahora la
  llama después de renombrar y recalcula `vector_equivalentes`.

### Added
- Nuevo chequeo en Configuración, "🔁 Ingredientes duplicados dentro de una misma receta", con un
  botón "Fusionar" por receta afectada -- se usó para limpiar las 4 recetas que quedaban en
  producción.
- Roadmap (`BUGS.md`): `FR-007` (agregar ingredientes sueltos directo a "Menú del día", sin pasar
  por una receta) y `FR-008` (clonar un menú de una persona a otra, para ajustar después) nuevos;
  `FR-004` (lista de súper) actualizado para permitir elegir más de una persona a la vez (dos
  personas que viven juntas y hacen un solo súper).

## [0.16.0] - 2026-08-30

### Changed
- **Las recetas de un mismo tiempo en el PDF de "Menú semanal" ahora se acomodan a dos
  columnas**, a pedido del usuario (seguía sobrando la mitad derecha de la hoja tras el afinado
  de 0.15.0): `_bloque_recetas()` (nuevo en `pdf_semanal.py`) empareja las recetas de dos en dos,
  lado a lado, con cada tabla a la mitad del ancho de página; si el tiempo tiene un número impar
  de recetas, la última va sola a ancho completo en vez de dejar una columna vacía. Cada par (o
  la receta suelta) va en un `KeepTogether` para que no se separen en un salto de página.

## [0.15.0] - 2026-08-30

### Changed
- **Afinado el PDF de "Menú semanal"**, a pedido del usuario, mismo día del rediseño de 0.14.0:
  - La tabla de cada receta ahora separa **Grupo | Cantidad | Alimento** en columnas propias (una
    fila por ingrediente) en vez de "cantidad — alimento" apilados dentro de una sola celda de
    texto. La celda de Grupo se fusiona verticalmente sobre las filas de ese grupo (`SPAN`), sin
    repetir el chip de color por ingrediente.
  - Letra más chica en todo el documento (título, nombre de menú, tiempos, recetas, ingredientes)
    para que quepa más contenido por hoja.
  - **Ya no hay salto de página forzado entre menús** -- fluyen uno tras otro (separados por una
    línea delgada) y ReportLab solo pasa de página cuando de verdad no cabe más, para no gastar
    una hoja completa por cada menú corto. Cada receta (nombre + tabla) va en un `KeepTogether`
    para que no se corte a la mitad justo en un salto de página.
  - Márgenes de página reducidos (16mm -> 10mm) para aprovechar más el ancho/alto disponible.

## [0.14.0] - 2026-08-30

### Changed
- **Rediseño completo del PDF de "Menú semanal"**, a pedido del usuario, tras revisar cómo usaba
  de verdad `menu-Sep.xlsx` (fuera de git): la v1 (0.12.0) era una cuadrícula de 7 días x 5
  tiempos con solo el nombre de cada receta -- lo que de verdad necesitaba era identificar rápido
  la relación entre el EQUIVALENTE y el INGREDIENTE real, organizado **por menú** (no por día),
  con una nota de a qué días aplica cada uno, igual que ese Excel.
  - Ahora un bloque por cada menú con nombre de la persona (salto de página entre uno y otro):
    nombre + "Aplica: {días}" (o "Sin día asignado todavía"), y por cada receta de cada tiempo,
    una fila por grupo SMAE con su chip de color + EQ y la cantidad real de cada ingrediente
    (`escalar_cantidad()`/`paso_equivalente()`, mismas funciones que "Menú del día" -- con
    fallback a "N equiv." si el alimento ya no está en el catálogo).
  - Chips de "Objetivo diario" (una vez, arriba) y "Total real de este menú" (al final de cada
    bloque) siguen usando los mismos `GRUPO_COLOR` de siempre, ahora con una etiqueta corta
    (`ETIQUETA_CORTA`, nueva en `pdf_semanal.py`) porque los nombres largos de `GRUPO_ETIQUETA`
    no caben en las columnas fijas de estas tablas.
  - Página vertical (carta) en vez de horizontal -- ya no hace falta el ancho de 7 columnas.
  - `generar_pdf_semanal()` ahora recibe también `catalogo` (`cargar_catalogo()`) para poder
    resolver la cantidad real de cada ingrediente.
  - `tests/test_pdf_semanal.py` reescrito para la nueva forma de los datos.

## [0.13.0] - 2026-08-29

### Changed
- **"Menú del día" → "Ver recetas de todas las personas" arranca marcado por default**, a pedido
  del usuario (antes arrancaba desmarcado).
- **Cada receta agregada a un tiempo ahora colapsa/expande su detalle de ingredientes**, a pedido
  del usuario: el contenido vive en un `st.expander`. Al agregar una receta nueva, las demás de
  ese tiempo se colapsan solas y la recién agregada queda expandida -- así la lista no se vuelve
  interminable de steppers conforme se arma el día. El botón "quitar" (ahora un ícono 🗑️) se movió
  fuera del expander para poder quitar una receta sin tener que expandirla primero.
  - **Corregido el mismo día tras QA en vivo**: el primer intento sobreescribía
    `st.session_state[key]` antes del rerun (mismo patrón que `_fecha_pendiente`), pero
    `st.expander` no es un widget "de valor" como `st.checkbox` -- una vez que su `key` existe,
    el navegador recuerda el toggle real del usuario y `expanded=` deja de tener efecto en
    reruns futuros, sin importar qué se deje en `session_state`. La única forma confiable de
    forzar el colapso es darle una key NUEVA a cada rerecuento ("epoch" que sube cada vez que se
    agrega otra receta, `st.session_state["_receta_epoch"]`) para que Streamlit trate el
    expander como recién creado y sí respete `expanded=` una vez más.

## [0.12.0] - 2026-08-29

### Added
- **"Menú semanal" → "📄 Descargar PDF para imprimir"**, a pedido del usuario (primera pieza de
  FR-003/Fase 5, adelantada como prueba): página horizontal (landscape carta) con los 7 días como
  columnas y los 5 tiempos como filas, letra grande y en negrita pensada para leerse de lejos
  (pegada en la cocina, reemplazando el uso que se le daba antes a un Excel armado a mano fuera de
  git). Usa los mismos `GRUPO_COLOR`/`GRUPO_ETIQUETA` de siempre -- no una paleta nueva -- para la
  fila de "Objetivo diario" (arriba) y "Total del día" (`actual_diario`, abajo de cada columna).
  Un día libre o con una referencia de menú rota se dibuja fusionado sobre las 5 filas de tiempo.
  Nuevo módulo `nutriguia/pdf_semanal.py` (ReportLab, agregado a `requirements.txt`) que no toca
  Mongo -- recibe los datos ya resueltos desde `views/menu_semanal.py`, mismo patrón que
  `nutriguia/validation.py`, con `tests/test_pdf_semanal.py` sobre datos sintéticos.
- `nutriguia/colores.py`: `color_texto_legible()` factorizado de la lógica interna de `chip_html()`
  (antes `_luminancia_relativa()` privada) para poder compartir el mismo criterio de contraste
  entre los chips HTML de la app y las tablas de color del PDF.

## [0.11.0] - 2026-08-29

### Added
- **"Agregar de SMAE" ahora soporta leche simple**, a pedido del usuario: las categorías "Leche
  descremada", "Leche semidescremada" y "Leche entera" de `SMAE_CONSULTA.csv` se catalogan como
  AOA cuando la porción sugerida de esa fila aporta al menos 7 g de proteína
  (`UMBRAL_PROTEINA_LECHE_AOA` en `nutriguia/smae_csv.py`) — por debajo de eso la fila se excluye,
  igual que una categoría no soportada. "Leche con azúcar" (helados, malteadas, leches
  saborizadas) se queda fuera a propósito, es una decisión distinta.
- Nuevo expander "¿Qué grupos cubre 'Agregar de SMAE'?" en la página "Guía" (`views/guia.py`)
  explicando qué categorías SMAE sí/no aparecen en ese buscador, incluida la regla de leche→AOA.

### Changed
- El caption al final de "Agregar de SMAE" (`views/editor_ingredientes.py`) ya no cita
  `CLAUDE.md` -- ahora enlaza con `st.page_link` a la página "Guía" (sección de arriba), para que
  la explicación quede donde el usuario final puede leerla sin salir de la app.

## [0.10.0] - 2026-08-29

### Changed
- **Picker de recetas de "Menú del día" ya no filtra estrictamente por tiempo**, a pedido del
  usuario: antes, un platillo etiquetado solo para "comida" simplemente no aparecía al armar
  "Cena", aunque en la práctica cualquiera puede servir. Ahora el `st.selectbox` muestra TODO el
  banco (filtrado solo por persona, como antes) — primero las recetas típicas de este tiempo en
  orden alfabético, luego el resto también alfabético con su primer tiempo típico como sufijo
  (ej. "Pan Francés · Desayuno"). Al elegir una receta que no es típica del tiempo actual, la
  línea de preview del vector de equivalentes muestra además un chip gris "Normalmente: {tiempo}"
  justificado a la derecha (`chip_muted_html()`, nuevo en `nutriguia/colores.py`) — el
  `st.selectbox` de Streamlit no soporta HTML por opción, así que el color/alineación real solo es
  posible en esa línea de preview, no dentro de la lista desplegable en sí.
- **Sincronizados los tags `al_despertar`/`desayuno` en `recetas.tiempo_tipico`**, a pedido del
  usuario: no todas las personas distinguen esos dos tiempos (algunos periodos de origen solo
  registraron uno para lo que es, en la práctica, la primera comida del día). Toda receta con uno
  de los dos ahora tiene también el otro — 31 recetas actualizadas
  (`scripts/migraciones/2026-08-29-sincronizar-al-despertar-desayuno.py`, ejecutado una vez sobre
  los datos existentes). Ver nota en `schema.md` para mantener la convención en recetas nuevas.

## [0.9.0] - 2026-08-29

### Changed
- **Corrección de diseño en "Menú semanal"**, a pedido del usuario: el flujo real es armar un día
  completo en "Menú del día" y darle un **nombre** ahí mismo para reutilizarlo, no mantener un
  segundo picker de recetas más simple en "Menú semanal". Se retiró por completo la colección
  `plantillas_semana` (nunca llegó a tener datos reales) y "Menú semanal" pasó a ser una
  herramienta puramente de asignación/consulta:
  - `menus_construidos` gana un campo opcional `nombre` (único por persona entre los días CON
    nombre, validado en código al guardar — no es un índice de Mongo). "Menú del día" ahora tiene
    un campo "Nombre (opcional)" junto a la fecha; ponerle nombre a un día es lo que lo vuelve
    elegible en "Menú semanal".
  - "Menú semanal" perdió su editor de menús (nombre + tabs de recetas sin steppers); "Tus menús"
    ahora es de solo lectura (nombre, fecha, equivalentes reales de cada día guardado), con un
    `st.page_link` directo a "Menú del día" para crear o editar.
  - "Configuración" actualizado: `_buscar_uso_de_receta()` y `_check_recetas_huerfanas()` ya no
    revisan `plantillas_semana` (colección retirada); `_check_asignacion_rota()` ahora compara
    `asignacion_semanal.dias` contra los nombres vigentes en `menus_construidos` en vez de
    `plantillas_semana`.
  - Diagrama de "Guía" simplificado de dos ramas a una cadena lineal (Ingredientes → Recetas →
    Menú del día → Menú semanal, con Personas alimentando a Menú del día) para reflejar que
    "Menú semanal" ya no arma recetas por su cuenta; corregido también el paso 4 de la guía en
    pasos, que describía el modelo viejo.
  - Ver `schema.md` para el detalle de `menus_construidos.nombre` y la nota de retiro de
    `plantillas_semana`.

## [0.8.3] - 2026-08-29

### Fixed
- Corrección sobre `0.8.2`: el `onclick` agregado ahí no hacía nada (Streamlit también elimina
  `onclick` de un `<a>` renderizado vía markdown). Los enlaces del diagrama de "Guía" en realidad
  siempre funcionaron -- Streamlit fuerza `target="_blank"` en todo `<a>` de markdown, así que
  abren en una pestaña nueva, no navegan en el mismo lugar. Quitado el `onclick` inerte y
  corregido el texto de la página para decir "se abre en una pestaña nueva" (ver `BUGS.md`
  BUG-008, reclasificado de RV a Closed -- no era un bug de la app).

## [0.8.2] - 2026-08-29

### Fixed
- Los enlaces del diagrama de "Guía" no navegaban al hacer clic (ver `BUGS.md` BUG-008).

## [0.8.1] - 2026-08-29

### Fixed
- Nodos del diagrama de "Guía" se veían como enlaces azules subrayados en vez de tarjetas (ver
  `BUGS.md` BUG-007).

## [0.8.0] - 2026-08-29

### Added
- Página "Guía" (`views/guia.py`, icono 📖): diagrama interactivo (CSS puro, sin JS) de cómo se
  relacionan Personas/Ingredientes/Recetas/Menú semanal/Menú del día, con enlaces reales a cada
  página y resaltado al pasar el cursor (`:has()`), más una guía corta en pasos para armar el
  primer Menú semanal.

### Changed
- Barra lateral reorganizada en secciones ("Guía", "Tu día a día", "Tus recetas", "Cuenta",
  "Ajustes") en vez de una lista plana, con títulos de nav más cortos ("Recetas" en vez de
  "Editor de recetas", etc.) — a pedido del usuario, para que se sienta más orgánica/intuitiva.
  "Menú del día" sigue siendo la página de entrada.
- Quitadas las menciones a "Mongo" en texto visible para el usuario (quedan solo en
  docstrings/comentarios de código, no en `st.caption`/`st.warning`/etc.).

## [0.7.1] - 2026-08-29

### Added
- Configuración → Ingredientes huérfanos: opción B para reemplazar un huérfano por un alimento
  ya existente en el catálogo (no solo catalogarlo como nuevo).
- Configuración → Posibles duplicados: botón "Son diferentes" para descartar un par sugerido
  (nueva colección `duplicados_descartados`, reversible desde la misma sección); la lista ahora
  muestra la `cantidad_por_equivalente` de cada lado del par.

## [0.7.0] - 2026-08-29

### Added
- Página "Configuración" (`views/configuracion.py`, ícono de engrane al final de la barra
  lateral): herramientas de administración/limpieza de datos.
  - Buscar relaciones: qué recetas usan un ingrediente, dónde se usa una receta (días guardados
    y menús semanales).
  - Chequeos automáticos, cada uno con su propia acción de arreglo: ingredientes huérfanos (se
    pueden catalogar ahí mismo), referencias a recetas eliminadas en menús semanales, vector de
    equivalentes desincronizado, posibles duplicados en el catálogo (enlaza al Editor de
    ingredientes con el alimento pre-seleccionado), personas sin objetivo, asignación semanal
    rota.

## [0.6.1] - 2026-08-29

### Fixed
- "Total de este tiempo" en Menú semanal mostraba el HTML del chip como texto plano en vez de
  la pastilla de color (ver `BUGS.md` BUG-006).

## [0.6.0] - 2026-08-29

### Added
- Página "Menú semanal" (`views/menu_semanal.py`): menús reutilizables por persona (solo
  selección de recetas por tiempo, sin ajuste de ingredientes) y su asignación a los 7 días de la
  semana, con un resumen de cobertura ("¿mi ciclo de menús cubre toda la semana?"). Nuevas
  colecciones `plantillas_semana` y `asignacion_semanal` (ver `schema.md`). Renombrar o eliminar
  un menú hace cascada a la asignación, mismo criterio que el editor de ingredientes con recetas.

### Changed
- **"Build your menu" se renombró a "Menú del día"** (título, archivo `views/menu_del_dia.py`, y
  todas las menciones en código/docs) para homologar el idioma de la app — ya no queda ninguna
  página con nombre en inglés.

## [0.5.2] - 2026-08-27

### Added
- Editor de ingredientes: al eliminar un alimento usado en recetas, checkbox opt-in "También
  quitarlo de las N receta(s) que lo usan" (`_quitar_de_recetas()`). Antes solo quedaba como
  ingrediente "no ajustable" para siempre; ahora se puede limpiar también de las recetas si de
  verdad no debería seguir ahí. Sin marcar el checkbox, el comportamiento es igual que antes.

## [0.5.1] - 2026-08-27

### Fixed
- Búsqueda del editor de ingredientes ("Buscar por nombre" y "Buscar en SMAE") era sensible a
  acentos — "atun" no encontraba "Atún". Nuevo `nutriguia/texto.py::normalizar_busqueda()`.

## [0.5.0] - 2026-08-27

### Added
- Página "Editor de ingredientes" (`views/editor_ingredientes.py`): tabla filtrable de todo
  `catalogo_alimentos` con conteo de uso en recetas, edición (con cascada de renombrado a
  `recetas` y fusión automática si el nuevo nombre ya existe) y eliminación con confirmación.
  Cierra `BUGS.md` FR-002.
- "Agregar de SMAE": buscador sobre `SMAE_CONSULTA.csv` (tabla oficial SMAE) para sumar alimentos
  nuevos al catálogo eligiendo la fila exacta (alimento + preparación + cantidad + unidad).
  `nutriguia/smae_csv.py` clasifica cada fila a uno de los 7 grupos canónicos (o libre); Azúcares/
  Leche/Alcohol no tienen equivalente y se excluyen.
- `SMAE_CONSULTA.csv` ahora vive en el repo (información pública, sin datos de personas reales —
  ver nota de privacidad en `CLAUDE.md`).
- `nutriguia/cantidades.py::formatear_decimal_como_fraccion()` + `tests/test_cantidades.py`,
  `tests/test_smae_csv.py` (corren en cualquier clon, el CSV ya no es dato privado).

### Changed
- `catalogo_alimentos.grupo` ahora puede ser `null` (alimento libre) — antes esos alimentos vivían
  fuera de la colección. Ver nota de diseño en `schema.md`.

## [0.4.2] - 2026-08-27

### Fixed
- El CSS de la identidad "Barro" se mostraba como texto plano visible en la página en vez de
  aplicarse (ver `BUGS.md` BUG-005). `inyectar_css()` ahora hace dos `st.markdown()` separados en
  vez de uno solo.

## [0.4.1] - 2026-08-27

### Added
- Identidad visual "Barro": paleta y tipografía propias (`.streamlit/config.toml` +
  `nutriguia/estilo.py`), inspiradas en una referencia de diseño del usuario y aprobadas primero
  como maqueta interactiva antes de tocar código real. Los 7 colores de grupo SMAE no cambiaron.
  Ver `UI-BUILD-YOUR-MENU.md` → "Identidad visual Barro y responsividad".

### Changed
- `chip_html()` ahora es una pastilla con contraste de texto automático (antes: rectángulo con
  texto blanco fijo, ilegible sobre colores claros como Fruta).
- Filas de ingrediente en "Build your menu" y en el Editor de recetas reestructuradas de 4-7
  columnas en una sola fila a 2 filas más cortas y agrupadas — mismo aspecto en escritorio, mejor
  comportamiento al apilarse en pantallas de teléfono (Streamlit apila `st.columns` bajo ~640px).

## [0.4.0] - 2026-08-27

### Added
- Día completo en "Build your menu" — los 5 tiempos (al despertar, desayuno, colación, comida,
  cena) vía `st.tabs`, con presupuesto restante calculado contra el objetivo diario.
- Guardado de planes por `(persona, fecha)` en `menus_construidos`, con upsert (una persona no
  puede tener dos planes para la misma fecha).
- Historial de planes guardados por persona, con reapertura de cualquier plan anterior
  (round-trip verificado: reabrir reconstruye exactamente lo guardado, ingrediente por
  ingrediente).

### Changed
- `schema.md` → `menus_construidos` reescrito para reflejar la forma real implementada
  (`fecha` obligatoria, snapshots `objetivo_diario`/`actual_diario`/`delta_diario`,
  `RecetaInstancia` como snapshot completo de ingredientes en vez de deltas).

## [0.3.6] - 2026-08-27

### Added
- Página "Personas" (crear persona nueva + editar objetivo diario de una existente), upsert de
  `personas`/`objetivos`.

## [0.3.5] - 2026-08-24 a 2026-08-25

### Added
- Editor de recetas (`views/editor_recetas.py`): crear/editar/eliminar recetas, bloquear
  ingredientes como no ajustables (`Ingrediente.bloqueado`), marcar ingredientes opcionales
  (`Ingrediente.opcional`) para fusionar variantes casi idénticas sin perder datos.
- Convención de colores por grupo SMAE (`nutriguia/colores.py`), reutilizada en toda la app.
- App multipágina vía `st.navigation`/`st.Page` (barra lateral).
- Auto-llenado de grupo y cantidad al elegir un alimento ya catalogado; cantidad se vuelve
  derivada (no editable) para alimentos catalogados al ajustar equivalentes.

### Fixed
- Ver `BUGS.md` — **BUG-001** (crash con ingredientes libres), **BUG-002** (pérdida de datos del
  campo `cantidad`), **BUG-003** (botón "Eliminar" no aparecía tras crear receta), **BUG-004**
  (grupo no se auto-llenaba por `session_state` obsoleto).

### Changed
- Deduplicación del banco de recetas en dos pasadas: 159→97 por nombre exacto, luego 97→86 por
  nombres parecidos (ver `CLAUDE.md` regla 9 y `scripts/migraciones/`, ambos fuera de git por
  contener datos reales).

## [0.2.0] - 2026-08-24

### Added
- `nutriguia/validation.py` — aritmética de equivalentes SMAE (contrato en `VALIDATION.md`).
- `tests/test_validation.py` — 34/34 menús históricos validados en verde.
- `app.py` — MVP Streamlit de un solo tiempo (Fase 3), presupuesto diario restante.

## [0.1.0] - 2026-08-24

### Added
- Estructura inicial del proyecto, documentos de diseño (`ARCHITECTURE.md`, `SETUP.md`,
  `schema.md`, `VALIDATION.md`, `UI-BUILD-YOUR-MENU.md`, `BUILD-PLAN.md`).
- MongoDB + `nutriguia/import_data.py` (Fase 0-1): catálogo de alimentos, recetas, menús
  históricos, personas y objetivos importados.

## Seguridad / privacidad

**2026-08-27** — el repo se hizo público. Se reescribió toda la historia de git
(`git filter-repo`) para purgar datos reales de nutrición/personas de commits previos, se
blindó `.gitignore` contra reintroducirlos, y se removieron nombres reales de la documentación
(reemplazados por "Persona A"/"Persona B"). No es una versión de producto — no lleva número de
versión propio, pero se documenta aquí porque afecta a cualquiera que haya clonado el repo antes
de esa fecha (ese clon tiene el historial viejo con datos reales y debe descartarse).
