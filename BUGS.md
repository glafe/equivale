# BUGS — bugs, caveats y feature requests

Registro vivo del *por qué* y *cómo* de cada problema/idea. `CHANGELOG.md` es la versión corta
para quien solo quiere saber *qué* cambió y *cuándo*; este archivo tiene el detalle. Al cerrar un
bug o enviar un feature, `CHANGELOG.md` recibe una línea con el ID de acá.

IDs son secuenciales y nunca se reutilizan dentro de cada serie.

## Contents

### Bugs
- Resueltos: [BUG-001](#bug-001--status-rv), [BUG-002](#bug-002--status-rv),
  [BUG-003](#bug-003--status-rv), [BUG-004](#bug-004--status-rv), [BUG-005](#bug-005--status-rv),
  [BUG-006](#bug-006--status-rv), [BUG-007](#bug-007--status-rv), [BUG-008](#bug-008--status-c),
  [BUG-009](#bug-009--status-rv)

### Known Caveats
- Abiertos: [KC-001](#kc-001), [KC-002](#kc-002)

### Feature Requests
- Propuestos: [FR-001](#fr-001), [FR-004](#fr-004), [FR-005](#fr-005), [FR-006](#fr-006),
  [FR-007](#fr-007), [FR-008](#fr-008)
- Parcialmente Shipped: [FR-003](#fr-003)
- Shipped: [FR-002](#fr-002)

## Severity guide

`Critical` (crash/pérdida de datos/falla total) · `High` (rotura mayor, sin workaround) ·
`Medium` (degradado, hay workaround) · `Low` (cosmético/menor/caso raro) · `Enh` (mejora menor).

## Status definitions

- Bugs: `O` Open · `IP` In Progress · `R` Resolved · `RV` Resolved & Verified · `C` Closed
- Caveats: `Active` · `Historical` · `Resolved <fecha>`
- Feature Requests: `Proposed` · `Planned` · `In Progress` · `Shipped` · `Declined`

---

## Bugs

### Detailed Entries

#### BUG-009 · [STATUS: RV]
**Title:** "🔗 Usar este" (reemplazar huérfano) dejaba ingredientes duplicados dentro de una receta
**Severity:** Medium
**Reported Date:** 2026-08-30
**Release Fixed:** 0.17.0

##### Observable Problem
El usuario notó, limpiando el catálogo a mano, que varias recetas tenían el mismo ingrediente
listado dos (o hasta tres) veces -- ej. "Crema de cacahuate" tres veces en "Pan tostado con
plátano", o "Res molida" dos veces en "Espagueti Boloñesa". Corrigió algunas a mano y pidió
revisar si quedaban más -- una consulta directa a Mongo encontró 4 recetas afectadas en total.

##### Fix Explanation (Exec Level — No Code)
"Editor de ingredientes" y "Configuración" tienen un botón "🔗 Usar este" para cuando un
ingrediente huérfano (sin catalogar) en realidad es el mismo alimento que uno que ya existe --
renombra el huérfano al nombre del existente en todas las recetas que lo usaban. El bug: si una
receta YA tenía un ingrediente con ese nombre (ej. la receta ya usaba "Nopales" Y tenía un
huérfano que también era, en el fondo, "Nopales" con otra ortografía), el renombrado dejaba DOS
filas con el mismo nombre en vez de fusionarlas en una -- inflando el conteo de equivalentes de
ese grupo sin que se notara a simple vista.

##### Fix Details (Technical)
Nueva función pura `fusionar_ingredientes_duplicados()` en `nutriguia/validation.py` (ver
`VALIDATION.md`): colapsa ingredientes con el mismo `alimento` sumando sus `equivalentes` -- el
total por grupo no cambia (es la misma suma repartida en una fila en vez de N), así que fusionar
es seguro sin revisar caso por caso. `_renombrar_en_recetas()` (duplicada en
`views/configuracion.py` y `views/editor_ingredientes.py`) ahora la llama después de renombrar, y
recalcula `vector_equivalentes`. Nuevo chequeo en Configuración,
"🔁 Ingredientes duplicados dentro de una misma receta" (`_check_ingredientes_duplicados_en_
receta()`), con un botón "Fusionar" por receta afectada -- se usó ese mismo botón, ya desplegado,
para limpiar las 4 recetas que quedaban en producción en vez de un script de migración aparte
(no se persiguió con un script porque la herramienta en la app ya cubre el caso permanentemente).

##### Workaround
Ninguno necesario tras el fix -- antes, corregir a mano desde el Editor de recetas.

#### BUG-008 · [STATUS: C]
**Title:** Los enlaces `<a href>` del diagrama de "Guía" no navegaban al hacer clic
**Severity:** Low
**Reported Date:** 2026-08-29
**Resolved Date:** 2026-08-29

##### Observable Problem
Al probar el diagrama de "Guía" con Playwright, hacer clic en un nodo no cambiaba la URL de la
página bajo prueba — parecía que el clic no hacía nada.

##### Fix Explanation (Exec Level — No Code)
No era un bug de la app: Streamlit fuerza `target="_blank" rel="noopener noreferrer"` en TODO
`<a>` que renderiza vía markdown (incluso con `unsafe_allow_html=True`, e incluso para un href
relativo/interno como estos) — el clic sí funcionaba, solo que abría la página destino en una
**pestaña nueva** del navegador en vez de navegar en el mismo lugar. El script de prueba
verificaba la URL de la MISMA pestaña, así que nunca iba a ver el cambio.

##### Fix Details (Technical)
Primer intento (equivocado): se agregó `onclick="window.location.href=...; return false;"` a
cada nodo, asumiendo que algo suprimía el comportamiento por default del `<a>`. Ese `onclick` no
hacía nada — Streamlit también elimina cualquier atributo `onclick` de un `<a>` renderizado vía
markdown (medida de sanitización, no configurable) — pero como el `target="_blank"` de por sí sí
funcionaba, el clic "se veía arreglado" cuando en realidad el `onclick` nunca se ejecutó. Se
confirmó la causa real usando `page.context.expect_page()` de Playwright (esperar una pestaña
nueva) en vez de revisar la URL de la pestaña original. Se quitó el `onclick` (inerte) y se
actualizó el texto de la página para decir "se abre en una pestaña nueva" en vez de implicar
navegación en el mismo lugar.

##### Workaround
Ninguno necesario — el comportamiento real (abrir en pestaña nueva) es aceptable para una página
de ayuda; solo hacía falta que el texto de la UI lo describiera bien.

#### BUG-007 · [STATUS: RV]
**Title:** Los nodos del diagrama de "Guía" se veían como enlaces azules subrayados, no como tarjetas
**Severity:** Low
**Reported Date:** 2026-08-29
**Release Fixed:** 0.8.1

##### Observable Problem
En la página "Guía", el texto dentro de cada cuadro del diagrama (ej. "Personas", "Recetas")
salía en azul y subrayado -- el estilo de enlace por default del navegador, no el diseño de
tarjeta pensado (fondo, borde, texto oscuro sin subrayado).

##### Fix Details (Technical)
Streamlit aplica su propio color/subrayado a los `<a>` dentro de contenido markdown con un
selector más específico que una sola clase CSS (`.eqv-node`) -- por eso no le ganaba. Cambiado a
`a.eqv-node` (selector más específico) + `!important` en `color`/`text-decoration`, mismo
recurso que ya usa `nutriguia/estilo.py` para pelear contra estilos nativos de Streamlit.
Encontrado en QA visual con Playwright antes de anunciar el cambio como terminado (mismo hábito
que descubrió `BUG-005`/`BUG-006`).

#### BUG-006 · [STATUS: RV]
**Title:** "Total de este tiempo" en Menú semanal mostraba el HTML del chip como texto plano
**Severity:** Low
**Reported Date:** 2026-08-29
**Release Fixed:** 0.6.1

##### Observable Problem
En el editor de "Menú semanal", debajo de las recetas de un tiempo, la línea "Total de este
tiempo" mostraba el `<span style="...">` completo como texto literal en vez de la pastilla de
color esperada.

##### Fix Details (Technical)
`views/menu_semanal.py` usaba `st.caption(texto + _chips(...))` en vez de
`st.markdown(..., unsafe_allow_html=True)` para esa línea en particular -- el resto de los usos
de `_chips()` en el mismo archivo sí pasaban por `st.markdown` con `unsafe_allow_html=True` y se
veían bien; encontrado en QA visual con Playwright antes de anunciar el cambio como terminado
(mismo hábito que descubrió `BUG-005`).

#### BUG-005 · [STATUS: RV]
**Title:** El CSS de la identidad "Barro" se mostraba como texto plano en vez de aplicarse
**Severity:** High
**Reported Date:** 2026-08-27
**Release Fixed:** 0.4.2

##### Observable Problem
Al desplegar la identidad visual "Barro", el bloque completo de reglas CSS aparecía como texto
literal visible arriba del título de cada página, en vez de aplicarse silenciosamente. El resto
del estilo (colores, tipografía de encabezados, chips) sí se aplicaba — solo la sección final del
CSS se veía como texto.

##### Steps to Reproduce
1. Cargar cualquier página de la app tras desplegar `nutriguia/estilo.py`.
2. Esperado: sin texto visible de CSS, solo la app estilizada. Actual: el CSS completo aparece
   como un párrafo de texto plano antes del título.

##### Fix Explanation (Exec Level — No Code)
El código que inyecta el estilo visual mandaba las etiquetas de fuentes (Google Fonts) y el
bloque de estilos juntos en una sola instrucción. El intérprete de texto de Streamlit cortó ese
bloque a la mitad en la primera línea en blanco que encontró dentro del CSS, y mostró el resto
como texto normal en vez de aplicarlo como estilo.

##### Fix Details (Technical)
Streamlit renderiza `st.markdown(..., unsafe_allow_html=True)` pasando el contenido por un
parser tipo CommonMark antes de insertarlo en el DOM. Los tags `<link>` en `GOOGLE_FONTS_LINK`
califican como bloque HTML "tipo 6" (lista fija de tags), que termina en la primera línea en
blanco; al concatenarlos con `<style>...</style>` en la misma llamada sin una línea en blanco de
separación, el parser seguía dentro de ese bloque tipo 6 al llegar a `<style>` (en vez de
reconocerlo como el inicio de un bloque tipo 1 -- script/pre/style/textarea -- que sí tolera
líneas en blanco adentro), y la primera línea en blanco DENTRO del CSS cortaba el bloque a la
mitad. `nutriguia/estilo.py::inyectar_css()` ahora hace dos `st.markdown()` separados: uno para
los `<link>` de fuentes y otro, empezando limpio en su propia línea, para el `<style>`.

##### Workaround
Ninguno necesario tras el fix — no se detectó en producción real (encontrado en QA visual con
Playwright antes de anunciar el cambio como terminado).

#### BUG-004 · [STATUS: RV]
**Title:** El grupo SMAE no se auto-llenaba al elegir un alimento del catálogo en el editor
**Severity:** Medium
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Al elegir un alimento ya catalogado en el editor de recetas, la variable interna sí se
actualizaba pero el `selectbox` de Grupo en pantalla seguía mostrando el valor anterior (o vacío).

##### Fix Details (Technical)
`st.selectbox` ignora un `value`/`index` nuevo si su `key` ya tiene una entrada en
`st.session_state` de un render anterior. Fix: escribir explícitamente
`st.session_state[f"grupo_{fila_id}"]` con el grupo del catálogo *antes* de que ese widget se
vuelva a instanciar en el mismo run. Ver `views/editor_recetas.py`.

#### BUG-003 · [STATUS: RV]
**Title:** Botón "Eliminar" no aparecía inmediatamente tras crear una receta nueva
**Severity:** Low
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
Después de guardar una receta recién creada, el botón "Eliminar" (que solo debe verse para
recetas ya existentes) no aparecía hasta refrescar manualmente.

##### Fix Details (Technical)
`receta_id` se asignaba después del `st.rerun()` en vez de antes, así que el rerun repintaba con
el `receta_id` viejo (vacío). Fix: mover la asignación antes del `rerun()`.

#### BUG-002 · [STATUS: RV]
**Title:** El campo `cantidad` de un ingrediente se podía perder al editar una receta
**Severity:** High
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
El editor de recetas no traía un campo para `cantidad` en el formulario de ingredientes; al
guardar una receta editada, ese campo se sobreescribía con `""`, borrando el dato real de
`cantidad_por_equivalente` histórico (afectó a `alambre-de-pollo-v2`: "150 g"/"½ tz" perdidos).

##### Fix Details (Technical)
Se agregó el campo `cantidad` al formulario de ingredientes en `views/editor_recetas.py`. El
documento corrupto en Mongo se restauró manualmente con los valores originales.

##### Prevention
Este es el caso concreto que motivó **BUG-002 (Enh) → auto-llenado de cantidad desde el
catálogo** (ver 5d7399e / 1aa2f83): si el alimento está catalogado, `cantidad` ahora se deriva de
`equivalentes` y deja de ser editable a mano, eliminando esta clase de error.

#### BUG-001 · [STATUS: RV]
**Title:** Crash del editor con ingredientes "libres" (`grupo_smae: null`, `equivalentes: 0`)
**Severity:** Critical
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Abrir cualquier receta con un ingrediente libre (ej. Canela, Salsa casera, Gelatina — 18 recetas
afectadas) tiraba `StreamlitValueBelowMinError` en el editor.

##### Steps to Reproduce
1. Abrir el editor de recetas.
2. Elegir una receta con un ingrediente sin grupo SMAE (ej. "Tinga de Pollo").
3. Esperado: el ingrediente se muestra con equivalentes=0. Actual: excepción, página rota.

##### Fix Explanation (Exec Level — No Code)
El stepper de equivalentes tenía un mínimo de 1 fijo para todos los ingredientes, pero los
ingredientes "libres" (sin grupo, cantidad al gusto) legítimamente valen 0 equivalentes.

##### Fix Details (Technical)
`number_input(min_value=1, ...)` aplicado incondicionalmente → cambiado a
`min_value = 0 if grupo_smae is None else 1`, más un clamp defensivo del `session_state` si el
usuario reasigna un grupo real a un ingrediente que era libre. Diagnosticado leyendo el
traceback embebido en un HAR de red (`Hars/192.168.68.59.har`, fuera de git) sin acceso directo a
logs del servidor.

---

## Known Caveats

### Detailed Entries

#### KC-002
**Title:** Kernels Linux 6.19–7.0.13 crashean MongoDB 8.0.x (bug de TCMalloc/rseq)
**Date Identified:** 2026-08-24
**Status:** Active (mientras el servidor corra un kernel en ese rango)

##### Exec Description
MongoDB no arrancaba en el servidor de producción hasta aplicar un workaround de compatibilidad
de kernel — no es un bug de este proyecto.

##### Eng Description
Bug conocido de glibc/TCMalloc con la syscall `rseq` en esa ventana de versiones de kernel.
Workaround: override de systemd con `Environment=GLIBC_TUNABLES=glibc.pthread.rseq=1` (ver
`SETUP.md`). No requiere cambios de código, solo de configuración del servicio.

##### Alternative Solutions
1. **Elegido** — override de systemd (`GLIBC_TUNABLES`), no invasivo, documentado en `SETUP.md`.
2. Downgrade de kernel — descartado, complica actualizaciones de seguridad del SO.
3. Downgrade de MongoDB — descartado, no atacaba la causa raíz.

#### KC-001
**Title:** Ingredientes con el mismo alimento real pero ortografía distinta quedan como
opcionales separados tras la fusión mecánica de recetas
**Date Identified:** 2026-08-25
**Status:** Active

##### Exec Description
Al fusionar recetas duplicadas por nombre exacto, si el mismo alimento aparecía escrito distinto
entre variantes (ej. "Atún" vs "Atún en agua", "Proteína" vs "Proteína en polvo"), el script de
fusión no los reconoció como el mismo ingrediente y quedaron como dos ingredientes opcionales
separados en la receta fusionada, en vez de uno solo.

##### Eng Description
`scripts/migraciones/2026-08-25-fusionar-recetas-por-nombre.py` compara nombres de ingrediente de
forma exacta (normalizado solo en mayúsculas/espacios) para decidir "está en todas las variantes"
vs. "solo en algunas" → opcional. No hay matching difuso. La pasada del 2026-08-25 (nombres
parecidos) corrigió ~16 casos detectados a mano, pero no se persiguió exhaustivamente en el resto
del banco (86 recetas).

##### Alternative Solutions
1. **Elegido (por ahora)** — corregir a mano desde el Editor de recetas si se nota al usar la
   app; bajo impacto (duplica un ingrediente opcional, no rompe la aritmética de equivalentes).
2. Matching difuso de nombres en el script de fusión — no implementado, riesgo de falsos
   positivos (fusionar alimentos que en realidad son distintos) mayor que el beneficio para un
   banco de 86 recetas.

---

## Feature Requests

### Detailed Entries

#### FR-008
**Title:** Clonar un menú de una persona a otra
**Date Requested:** 2026-08-30
**Status:** Proposed

##### Exec Description
Poder copiar un día ya armado y guardado con nombre (ej. "Menú 1" de Persona A) hacia otra
persona, para usarlo como punto de partida en vez de armar todo desde cero -- y después poder
ajustar cantidades/ingredientes ya del lado de la persona destino sin afectar el original.

##### Eng Description
Distinto de `FR-005` (duplicar un día para la MISMA persona): aquí el `persona` cambia. Reutiliza
`_instancia_desde_guardado()` de `views/menu_del_dia.py` para clonar cada `RecetaInstancia` con
`instancia_id` nuevo (ya lo hace hoy al "Abrir" un día del historial), pero el documento
resultante debe guardarse con el `persona` destino y, probablemente, sin arrastrar el `nombre`
tal cual (para no chocar con la regla de nombre único por persona -- aunque como es OTRA persona
técnicamente no colisiona, puede ser confuso tener "Menú 1" en dos personas por separado sin
dejarlo claro en la UI). El `objetivo_diario`/`estado`/`delta_diario` deben recalcularse contra el
objetivo de la persona destino, no copiarse tal cual -- los equivalentes de las recetas clonadas
casi seguro no van a cuadrar exacto con el objetivo de la nueva persona, y esa es justo la parte
que el usuario espera "ajustar después" (steppers ya existentes en "Menú del día", ninguna
herramienta nueva ahí). Probablemente vive como un botón "Clonar a otra persona" junto a "Abrir"
en el historial de "Menú del día", con un selector de persona destino.

##### Dependencies
Ninguna -- reutiliza mecanismos ya existentes de "Menú del día".

#### FR-007
**Title:** Agregar ingredientes sueltos directo a "Menú del día" (sin pasar por una receta)
**Date Requested:** 2026-08-30
**Status:** Proposed

##### Exec Description
A veces conviene comer un alimento suelto (ej. una fruta) sin que forme parte de ninguna receta
del banco -- poder agregarlo directo a un tiempo de "Menú del día", igual que se agrega una
receta, en vez de tener que crear una "receta" de un solo ingrediente en el banco solo para eso.

##### Eng Description
`dia["tiempos"][tiempo]` es una lista de `RecetaInstancia` (`instancia_id`, `receta_id`, `nombre`,
`ingredientes`) -- un ingrediente suelto encajaría como una `RecetaInstancia` sintética con un
solo ingrediente y sin `receta_id` real (o un `receta_id` sentinela tipo `None`/`"__suelto__"`
para no confundirse con una receta de verdad al buscar "dónde se usa"). Necesita un picker
separado del de recetas (buscar directo en `cargar_nombres_alimentos()`/`catalogo_alimentos` en
vez de en `cargar_recetas()`), con su propio stepper de equivalentes (reutiliza
`paso_equivalente()`/`escalar_cantidad()` igual que cualquier ingrediente ajustable). Revisar que
`_check_recetas_huerfanas()`/`_buscar_uso_de_receta()` en Configuración no truenen con instancias
sin `receta_id` real.

##### Dependencies
Ninguna.

#### FR-006
**Title:** Detector de posibles duplicados en el catálogo de ingredientes
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
En el Editor de ingredientes, un botón que compare los nombres del catálogo por similitud (no
exacta) y muestre pares sospechosos para revisar y fusionar con un clic, en vez de encontrarlos a
ojo mientras se usa la app.

##### Eng Description
Cierra `KC-001` de raíz (ej. "Aceite de oliva" vs "Aceite oliva"). La fusión ya existe en
`views/editor_ingredientes.py` (ver el flujo de colisión de nombre al renombrar) — esto solo
automatiza encontrar los candidatos, probablemente con una distancia de edición simple
(Levenshtein) sobre los nombres normalizados de `nutriguia/texto.py`.

##### Dependencies
Editor de ingredientes (Shipped en `FR-002`).

#### FR-005
**Title:** Duplicar un día ya guardado como punto de partida
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
Un botón "Duplicar" junto a "Abrir" en el historial de "Menú del día" (o "Empezar como ayer" al
abrir la página) que clona un día ya guardado en vez de armar todo desde cero.

##### Eng Description
Reutiliza casi tal cual `_instancia_desde_guardado()` de `views/menu_del_dia.py` — la pieza más
barata identificada en la revisión de producto de 2026-08-29 (ver historial de conversación; no
hay un documento aparte, este es el registro canónico).

##### Dependencies
Ninguna.

#### FR-004
**Title:** Lista de súper generada
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
Un botón que suma los ingredientes de un día o de una semana planeada en una lista consolidada de
compras (ej. "Pollo: 90 g", "Tortilla: 6 piezas"), en vez de tener que releer cada receta.

##### Eng Description
Con `menus_construidos.nombre` + `asignacion_semanal` (ver `schema.md`, corregido 2026-08-29) ya
existe de dónde sacar "qué se come toda la semana": para cada día de la semana con un nombre
asignado, resolver el `menus_construidos` correspondiente (por `persona`+`nombre`), sumar sus
ingredientes reales (no solo el vector por grupo — hace falta una función nueva tipo
`sumar_por_alimento`, ver `nutriguia/validation.py` si se generaliza), y formatear la cantidad
total con `escalar_cantidad()`. También podría operar solo sobre un día de `menus_construidos`
sin esperar a tener una semana completa armada.

**Actualizado 2026-08-30, a pedido del usuario**: la selección de persona debe poder ser
**múltiple** (no una sola), para el caso de dos personas que viven juntas y hacen un solo súper —
sumar los ingredientes de ambas asignaciones semanales en una sola lista consolidada (mismo
alimento de Persona A y Persona B se suma en una sola línea, no dos separadas).

##### Dependencies
`menus_construidos.nombre`/`asignacion_semanal` (Shipped 2026-08-29, corregido el mismo día — ver
`CHANGELOG.md` 0.9.0) para la versión semanal; ninguna para una versión que solo opere sobre un
día de `menus_construidos`.

#### FR-003
**Title:** Fase 5 — pulido (semana completa, exportar imprimible, sugerencia automática de hueco)
**Date Requested:** 2026-08-24
**Status:** Parcialmente Shipped -- "exportar imprimible" salió en 0.12.0 (2026-08-29), adelantada
a pedido explícito del usuario como prueba, sin esperar al resto de la Fase 5. Las otras dos
(repetir semana completa, sugerencia automática de hueco) siguen bloqueadas a propósito.

##### Exec Description
Tres mejoras de pulido: repetir el flujo de día completo por semana (con aviso de repetición),
exportar un plan a formato imprimible, y sugerir automáticamente un ingrediente suelto del
catálogo cuando ningún combo del banco de recetas cuadra exacto con un objetivo.

##### Eng Description
Ver `BUILD-PLAN.md` → Fase 5 para el detalle de cada una. No empezar el resto sin haber usado la
Fase 4 en la vida real — puede cambiar qué vale la pena pulir primero.

> **"Exportar imprimible" shipped en 0.12.0** — `nutriguia/pdf_semanal.py` (ReportLab), botón en
> "Menú semanal". Ver `CHANGELOG.md` 0.12.0 y `UI-BUILD-YOUR-MENU.md` → "Menú semanal" para el
> detalle. Es una primera versión ("hagamos la prueba", palabras del usuario) -- falta ajustar
> tamaños/diseño según feedback de uso real antes de darla por terminada del todo.
>
> **Motor cambiado de PDF a HTML en 0.18.0 (2026-08-30)** — a pedido del usuario, que prefiere que
> EquiVale genere el HTML y usar el "Imprimir a PDF" de su propio navegador (control total de
> márgenes/escala). `nutriguia/pdf_semanal.py` (ReportLab) se retiró; `nutriguia/html_semanal.py`
> lo reemplaza con el mismo diseño visual. Ver `CHANGELOG.md` 0.18.0 y `UI-BUILD-YOUR-MENU.md` →
> "Del PDF al HTML".

##### Dependencies
Fase 4 (día completo + guardado + historial) — completa desde 2026-08-27.

#### FR-002 · [STATUS: Shipped 0.5.0]
> **Shipped en 0.5.0** — implementado como página nueva "Editor de ingredientes"
> (`views/editor_ingredientes.py`) en vez de dentro del editor de recetas: tabla del catálogo
> completo con edición/eliminación (con cascada de renombrado a `recetas`, ver
> `UI-BUILD-YOUR-MENU.md`), más el buscador "Agregar de SMAE" descrito abajo.
> `SMAE_CONSULTA.csv` se commiteó al repo (es información pública, ver nota de privacidad en
> `CLAUDE.md`) en vez de depender de que cada quien lo consiga aparte.

**Title:** "EquiVale Chef" — integración con `SMAE_CONSULTA.csv` para agregar alimentos nuevos al
catálogo desde el propio editor
**Date Requested:** 2026-08-24

##### Exec Description
Cuando un alimento nuevo no está en `catalogo_alimentos`, poder buscarlo en la tabla oficial SMAE
(`SMAE_CONSULTA.csv`) y fijar su equivalencia sin salir del editor de recetas.

##### Eng Description
Si el alimento tampoco está en `SMAE_CONSULTA.csv`, marcar `asuncion: true` y pedir confirmación
del criterio usado — mismo criterio que la regla 5 de `CLAUDE.md`. Ver `BUILD-PLAN.md` → "Ideas
para más adelante" para el detalle completo.

##### Dependencies
Editor de recetas (Fase 3.5) — ya construido, esto es la extensión pendiente.

#### FR-001
**Title:** Historial de versiones del objetivo por persona
**Date Requested:** 2026-08-27
**Status:** Proposed

##### Exec Description
Poder ver qué objetivo diario tenía una persona en una fecha pasada, no solo el vigente.

##### Eng Description
La página "Personas" (Fase 3.6) solo mantiene UN documento `objetivos` vigente por persona
(upsert in-place). El schema ya deja `vigente_desde` listo para esto, pero no se guarda
histórico de valores anteriores al hacer un nuevo upsert. Retomar solo si hace falta consultar
"qué objetivo tenía tal persona en tal fecha".

##### Dependencies
Ninguna — se puede implementar en cualquier momento cambiando el upsert por un insert +
`vigente_desde`/`vigente_hasta`.
